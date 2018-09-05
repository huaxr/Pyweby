import types
import json
import time
import sys
import threading
import os
import copy
import six
from functools import wraps
from collections import OrderedDict
import traceback as tb

from handle.request import HttpRequest,Unauthorized,MetaRouter
from handle.exc import (StatusError,MethodNotAllowedException,
                        EventManagerError,NoHandlingError,JsonPraseError,_HttpException)
from concurrent.futures import _base
from util.Engines import EventFuture,Eventer
from util.logger import Logger,traceback
from core._concurrent import safe_lock
from util._compat import EXCEPTION_MSG,SET,HAS


_STATUS_CODES = {
    100:    'Continue',
    101:    'Switching Protocols',
    102:    'Processing',
    200:    'OK',
    201:    'Created',
    202:    'Accepted',
    203:    'Non Authoritative Information',
    204:    'No Content',
    205:    'Reset Content',
    206:    'Partial Content',
    207:    'Multi Status',
    226:    'IM Used',              # RFC 3229
    300:    'Multiple Choices',
    301:    'Moved Permanently',
    302:    'Found',
    303:    'See Other',
    304:    'Not Modified',
    305:    'Use Proxy',
    307:    'Temporary Redirect',
    400:    'Bad Request',
    401:    'Unauthorized',
    402:    'Payment Required',     # unused
    403:    'Forbidden',
    404:    'Not Found',
    405:    'Method Not Allowed',
    406:    'Not Acceptable',
    407:    'Proxy Authentication Required',
    408:    'Request Timeout',
    409:    'Conflict',
    410:    'Gone',
    411:    'Length Required',
    412:    'Precondition Failed',
    413:    'Request Entity Too Large',
    414:    'Request URI Too Long',
    415:    'Unsupported Media Type',
    416:    'Requested Range Not Satisfiable',
    417:    'Expectation Failed',
    418:    'I\'m a teapot',  # RFC 2324
    422:    'Unprocessable Entity',
    423:    'Locked',
    424:    'Failed Dependency',
    426:    'Upgrade Required',
    428:    'Precondition Required',  # RFC 6585
    429:    'Too Many Requests',
    431:    'Request Header Fields Too Large',
    449:    'Retry With',  # proprietary MS extension
    451:    'Unavailable For Legal Reasons',
    500:    'Internal Server Error',
    501:    'Not Implemented',
    502:    'Bad Gateway',
    503:    'Service Unavailable',
    504:    'Gateway Timeout',
    505:    'HTTP Version Not Supported',
    507:    'Insufficient Storage',
    510:    'Not Extended'
}


Log = Logger(logger_name=__name__)

def _cache_result(**kwargs):
    '''
    wrapper for cache result from the api 's result.
    '''
    def wrapper(func):
        @wraps(func)
        def savvy(*_args,**_kwargs):
            print(_args)
            return CacheEngine(func, CacheContainer(**kwargs))

        return savvy

    return wrapper

def cache_result(**kwargs):
    '''
    cache result purpose.
    '''
    def wrapper(func):
        return CacheEngine(func, CacheContainer(**kwargs))
    return wrapper


class CacheEngine(object):

    def __init__(self, function, cache=None, *args, **kwargs):
        self.function = function
        if cache:
            self.cache = cache
        else:
            self.cache = CacheContainer()
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        if kwargs.pop('format', None) is None:
            # format like: `filename:function:args`
            filename = os.path.basename(sys._getframe(1).f_code.co_filename).split('.')[0]
            key = ':'.join([filename, getattr(self.function, '__name__'), repr((args, kwargs))])

        else:
            # if you want ignore parameter specific value, set the
            # format True
            import inspect, hashlib
            key = inspect.signature(self.function) or \
                  hashlib.md5(sys._getframe(0).f_code.co_code).hexdigest()[:10]
        try:
            return self.cache[key]

        except KeyError:
            value = self.function(*args, **kwargs)
            self.cache[key] = value
            return value


class CacheContainer(object):

    def __init__(self, **kwargs):
        self.max_size = kwargs.pop('max_size', 100)
        assert isinstance(self.max_size,int) and self.max_size>0
        self.expiration = kwargs.pop('expiration', 60 * 5)
        assert isinstance(self.expiration, int) and self.expiration > 0
        self.concurrent = kwargs.pop('concurrent', False)
        self._CacheResult = {}
        self._expires = OrderedDict()
        self._accesses = OrderedDict()
        if self.concurrent:
            self._rlock = threading.RLock()

    @safe_lock
    def size(self):
        return len(self._CacheResult)

    @safe_lock
    def clear(self):
        self._CacheResult.clear()
        self._expires.clear()
        self._accesses.clear()

    def __contains__(self, key):
        return self.has_key(key)

    @safe_lock
    def has_key(self, key):
        return key in self._CacheResult

    @safe_lock
    def __setitem__(self, key, value):
        t = int(time.time())
        del self[key]
        self._CacheResult[key] = value
        self._accesses[key] = t
        self._expires[key] = t + self.expiration
        self.cleanup()

    @safe_lock
    def __getitem__(self, key):
        t = int(time.time())
        del self._accesses[key]
        self._accesses[key] = t
        self.cleanup()
        return self._CacheResult[key]

    @safe_lock
    def __delitem__(self, key):
        if key in self._CacheResult:
            del self._CacheResult[key]
            del self._expires[key]
            del self._accesses[key]

    @safe_lock
    def cleanup(self):

        if self.expiration is None:
            return None
        '''
        some Python Versions does't allow del items when itering sequence object.
        if you do this, some Exception will be raised like below.
        `RuntimeError: OrderedDict mutated during iteration`
        so , make a duplicate for it is a considerable way.
        '''
        duplicate = copy.deepcopy(self._expires)

        for k in duplicate:
            if duplicate[k] < int(time.time()):
                del self[k]
            else:
                break

        while (self.size() > self.max_size):
            for k in self._accesses:
                del self[k]
                break


class restful(object):
    def __init__(self,fn):
        self.fn = fn

    def __get__(self, instance, cls=None):

        if instance is None:
            return self
        result = self.fn(instance)
        # assert isinstance(result,(list,tuple)) and len(result) == 2
        tmp = {}
        if isinstance(result, (list, tuple)) and len(result) == 2:
            tmp['res'] = result[0]
            tmp['status'] = result[1]
        else:
            tmp['res'] = result
            tmp['status'] = 200
        try:
            json.dumps(tmp)
        except Exception:
            raise JsonPraseError('Error format')
        return tmp


def check_param(fn):
    def wrapper(self,router,method):
        #TODO, later usage add methods.
        if method not in ['get','post',b'get',b'post']:
            raise ValueError('%s is not allowed method' %method)
        return fn(self,router,method)
    return wrapper


@six.add_metaclass(MetaRouter)
class HttpResponse(object):

    def add_future_result(self,*args,**kwargs):
        raise NotImplementedError



class DangerResponse(HttpResponse):
    def __init__(self,*args,**kwargs):
        # self.status = status
        # self.headers = headers
        # self.body = body
        pass

    def catch_except(self, may_exception):
        try:
            eval(may_exception)
        except MethodNotAllowedException as e:
            print(e)

    def ok_body(self,body):
        #TODO sync is not supported yet , finished at   8.16
        if isinstance(body,_base.Future):
            '''
            client code usually does not ask whether the Future
            is .done(), but will wait for the notification.
            
            so, the Future class has add_done_callback() method
            witch has one parameter that is callable object, and 
            will be called where the Future.done() == True event
            happens.(calling the argument pass in the add_done_callback)

            notes:  .result() method can accept timeout=int as parameter,
            when block timeout, `TimeoutError` will be raised. 
            '''

            #self is WrapResponse, add_done_callback(fn) finally call fn(self)
            body.add_done_callback(self.callback_result)

    def callback_result(self,*args):
        raise NotImplementedError

    def gen_body(self):
        raise NotImplementedError


    def transe_format(self,arg):
        raise NotImplementedError






class WrapResponse(DangerResponse):

    def __init__(self,wrapper_request,event_manager=None,sock=None,PollCycle=None,**kwargs):

        assert issubclass(wrapper_request.__class__,HttpRequest)

        self.wrapper = wrapper_request
        self.event_manager = event_manager
        self.sock = sock
        self.PollCycle = PollCycle
        self.kwargs = kwargs  # middleware from request

        try:
            self.tuples = self.wrapper.get_first_line
        except MethodNotAllowedException:
            self.tuples = ('pyweby',None,None,'HTTP/1.1')

        self.method = self.tuples[0].lower()
        self.path = self.tuples[1]
        self.query = self.tuples[2]
        self.version = self.tuples[3]
        self.msg_pair = {200: 'OK',
                         301: 'Permanently Moved',
                         302: 'Moved Temporarily',
                         400: 'Bad Request',
                         401: 'Unauthorized',
                         403: 'Forbidden',
                         404: 'Not Found',
                         405: 'Method Not Allowed',
                         500: 'Internal Server Error',
                         502: 'Bad Gateway'}

        self.headers = {}

        super(WrapResponse,self).__init__()

    def __repr__(self):
        return repr('pyweby')


    @check_param
    def auth_check(self,router,method):
        '''
        checking whether cookie has passed authentication or declassified content
        is correct.
        :param router: the router find_handler returns
        :param method: support `get`,`post` , later usage is limit now.
        :return:
        '''
        if hasattr(router, '_login_require'):
            cookies = router.request.get_cookie()

            # cookies may be None. if None means Unauthorized.
            if cookies:
                nexter = getattr(router, method)
            else:
                r = Unauthorized()
                nexter = getattr(r, method)
        else:
            nexter = getattr(router, method)

        return nexter

    def get_writer(self):
        return self.wrapper.conn_obj


    def switch_method(self,method=None):
        '''
        here is decided to branch , the user define class has the router string ,
        which is reference by this method
        :return:
        '''
        nexter = (None,None)   # for staring the coroutine
        while True:
            yield nexter
            handler = self.find_handler()
            router, _re_res = handler[0], handler[1]
            ROUTER = router()

            # call before_request before the find_handler.
            # you need call `bound method` of before_request.
            # or will missing self parameter
            '''
            >>> if HAS(ROUTER, 'before_request'):
            >>>     before = getattr(ROUTER,'before_request')
            >>>     before()
            '''

            # router is response , we add the request attribute to the self instance
            # 1.the WrapperRequest object
            SET(ROUTER,'request',self.wrapper)
            # 2. the global application instance binding here,this is an instance already
            SET(ROUTER,'app',self.wrapper.application)
            SET(ROUTER, 'matcher', _re_res)

            if method.upper() in ('GET',b'GET'):
                '''
                dispose GET method
                '''
                nexter = self.auth_check(ROUTER,'get')

            elif method.upper() in ('POST',b'POST'):
                '''
                handler POST method
                '''
                nexter = self.auth_check(ROUTER, 'post')

            else:
                '''
                this means we don't handler except GET,POST, TODO and 
                robust web server.
                '''
                nexter = self.auth_check(ROUTER, '')


    def discern_result(self,time_consuming_op=None):
        '''
        recognize the router to go, and generator response body and status!
        :return:
        '''

        # if self.method is not in the allowed list-methods, that self.method
        # is set `pyweby` , which means an mistakenly usage of http request method
        next(time_consuming_op)

        while True:
            result = time_consuming_op.send(None)
            time_consuming_op.close()

            if result:
                # when using cache_result for caching the result in CacheEngine
                # the descriptor will turn te result to be CacheEngine Object.
                if isinstance(result,(types.MethodType,dict,CacheEngine)):
                    return result

                elif isinstance(result,(str,bytes)):
                    body, status = result, 200

                elif isinstance(result,(tuple,list)) and len(result) == 2:
                    body, status = result[0], result[1]
                    assert isinstance(status,int) and  status in self.msg_pair.keys(), StatusError(status=status)

                elif isinstance(result,types.FunctionType):
                    body,status = result()

                else:
                    raise NoHandlingError('no handlering')

                '''
                for return result pretty only, never user json.dumps before , otherwise status is under prase
                too
                '''
                return json.dumps(body), status
            else:
                raise StopIteration("Error result at `discern_result`")


    def gen_headers(self,version, status, msg, add_header=None):
        tmp = []
        '''
        return the headers that contains the response prefix
        '''

        self.headers['Server'] = "Pyweby Web 1.0"
        # self.headers['Connection']= 'Keep-Alive'
        self.headers['first_line'] = "{version} {status} {msg}".format(version=version, status=status,msg=msg)

        if add_header and isinstance(add_header,dict):
            for k,b in add_header.items():
                if k not in self.headers.keys():
                    self.headers[k] = b

        if hasattr(self.wrapper,'__header__'):
            self.headers.update(self.wrapper.response_header)
            status_code = self.wrapper._status_code or 200
            self.headers['first_line'] = "{version} {status} {msg}".format(
                version=version,status=status_code or status, msg=self.msg_pair[status_code])

        # in Python3, ''.join(list) will raise `TypeError: sequence item 0: expected string, xx found`
        first_line = self.headers.pop('first_line')
        tmp.append(first_line)
        for pair in self.headers.items():
            tmp.append(': '.join(pair))

        header = '\r\n'.join(str(s) for s in tmp)
        # print(header)
        return header + "\r\n\r\n"


    def gen_exception_body(self,code,msg,status_message=None,pretty=True):
        if pretty:
            yield u'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
            yield u'<html>\n'
            yield u'<body>\n'
        yield u'<title>%(code)s </title>\n' %{'code':code}
        yield u'<h1>%(code)s %(description)s</h1>\n' %{'code':code, 'description':  self.get_exption_description(msg)}
        if status_message:
            yield u'%(status_message)s\n' %{'status_message':status_message}
        if pretty:
            yield u'</body>\n'
            yield u'</html>'


    def get_exption_description(self,msg):
        return u'<p>%s</p>' % msg


    def gen_html(self):
        pass


    def gen_body(self,  prefix="\r\n\r\n", if_need_result = False,debug=True):
        '''
        generator the body contains headers
        :param prefix: this prefix to tail whether the response package is integrity
        '''
        try:
            tmp = self.discern_result(time_consuming_op=self.switch_method(self.method))
            # tmp is <bound method testRouter.get>

            if isinstance(tmp, types.MethodType):
                # Do not try execute tmp() twice.
                if debug:
                    X_X_X = tmp()
                else:
                    try:
                        X_X_X =tmp()
                    except _HttpException:
                        return
                    except Exception as e:
                        Log.critical(traceback(e))
                        return self.not_future_body(500, '<h1>internal server error</h1>', prefix=prefix)

                # when no result return.
                if  X_X_X is None:
                    # You just need to generate a 302 hop and pass it to sock.
                    response_for_no_return = self.gen_headers(self.version, None, None)
                    return response_for_no_return

                if isinstance(X_X_X,(list,tuple)):
                    body,status = X_X_X
                else:

                    body,status = X_X_X,200    # 200 OK response for default.

            # when using @restful
            elif isinstance(tmp, dict):
                body ,status = tmp, tmp.get('status',502)

            # when using @cache_result
            elif isinstance(tmp, CacheEngine):
                body, status = tmp('')

            else:
                raise NoHandlingError


        except _HttpException as e:

            _exp = EXCEPTION_MSG(e)

            if len(_exp) == 2:
                e, status_message = EXCEPTION_MSG(e)
            elif len(_exp) == 1:
                e, status_message = _exp[0], None
            else:
                raise AttributeError("too many arguments")

            msg = self.msg_pair.get(e,None) or _STATUS_CODES.get(e)

            bodys = ''.join(list(self.gen_exception_body(str(e),msg,status_message)))
            add_header = {'Content-Type': 'text/html'}
            return self.gen_headers(self.version, int(e), msg,add_header=add_header)\
                   + str(bodys)


        except Exception as e:
            Log.warning(traceback(e))
            tb._context_message()
            return self.not_future_body(500, '<h1>internal server error</h1>', prefix=prefix)

        if isinstance(body,dict):
            return self.restful_body(body,status)

        elif isinstance(body, _base.Future):
            # WE DON'T NEED if_need_result FLAG ANYMORE,CAUSE WE CAN JUDGE THE BRANCH TO GO BY
            # distinguish whether body is Future or (str,bytes...)

            # 8.10
            # since from  switch_method getting called, the returning result can be
            # an normal bytes? or string? type for return.
            # but if you set concurrent generator a Future object
            # `<class 'concurrent.futures._base.Future'>` , so here you should judge
            # Whether `body` is Future.tp_repr or not.
            # ok_body is the method what you need?
            # no, still call result(), blocking still, how can i solve it?
            #
            # 8.14
            # solution: using Observer-Model to delegate the Future and current socket
            # to the EventMaster
            self.ok_body(body)

        else:
            return self.not_future_body(status, "".join(["<p>",str(body),"</p>"]), prefix)


    def callback_result(self,finished_future):
        # gen_body finishing will callback the method
        assert isinstance(finished_future, _base.Future)
        assert  finished_future.done() == True
        self.trigger_event(finished_future)


    def trigger_event(self,future):
        '''
        the function simulate a event_source like object, just for padding
        the EventManager Queue to handling delay Future result.
        '''
        if issubclass(EventFuture, Eventer):
            event = EventFuture(future,self.sock,_PollCycle=self.PollCycle)
            event.dict["type"] = u'futures'
            if self.event_manager is None:
                raise EventManagerError
            self.event_manager.addFuture(event)

        else:
            raise OSError("EventFuture must be new_class!")

    def not_future_body(self,status,body,prefix=None):

        assert isinstance(status,int)
        assert not isinstance(body, _base.Future)

        msg = self.msg_pair.get(status, 200)
        if prefix != u'\r\n' * 2:
            return json.dumps(body)
        else:
            return self.gen_headers(self.version, status, msg,add_header={'Content-Type': 'text/html'}) + str(body)

    def set_header(self,k,v):
        return {k:v}

    def restful_body(self,body,status):
        '''
        make header Content-Type":"application/json",
        the browser will parse it perfect.
        '''
        return self.gen_headers(self.version,
                                status,
                                self.msg_pair.get(status,200),
                                add_header=self.set_header("Content-Type","application/json")) + \
                                str(json.dumps(body))


    def render_embed_css(self, css_embed):
        return b'<style type="text/css">\n' + b'\n'.join(css_embed) + \
               b'\n</style>'

    def render_embed_js(self, js_embed):
        return b'<script type="text/javascript">\n//<![CDATA[\n' + \
               b'\n'.join(js_embed) + b'\n//]]>\n</script>'


    def render_linked_css(self, css_files_list):

        return ''.join('<link href="' + x + '" '
                       'type="text/css" rel="stylesheet"/>'
                       for x in css_files_list)

    def render_linked_js(self, js_files):
        return ''.join('<script src="' + x +
                       '" type="text/javascript"></script>'
                       for x in js_files)

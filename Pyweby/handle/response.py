import types
import json
import time

from handle.request import HttpRequest
from handle.exc import StatusError,MethodNotAllowedException,EventManagerError
from concurrent.futures import _base
from util.Observer import EventFuture,Eventer
from util.logger import Logger
import logging


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
        #TODO sync is not supported yet
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


class WrapResponse(DangerResponse):

    def __init__(self,wrapper_request,event_manager=None,sock=None,PollCycle=None):

        assert issubclass(wrapper_request.__class__,HttpRequest)

        self.wrapper = wrapper_request
        self.event_manager = event_manager
        self.sock = sock
        self.PollCycle = PollCycle

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
                         400: 'METHOD NOT ALLOWED',
                         404: 'NOT FOUND',
                         500: 'SERVER ERROR'}

        self.headers = {}

        self.Log = Logger(logger_name=__name__)
        self.Log.setLevel(logging.INFO)


        super(WrapResponse,self).__init__()


    def get_writer(self):
        return self.wrapper.conn_obj

    def find_handler(self):
        return self.wrapper.find_router()


    def switch_method(self,method=None):
        '''
        here is decided to branch , the user define class has the router string ,
        which is reference by this method
        :return:
        '''
        nexter = (None,None)   # for staring the coroutine

        def callback(*args, **kwargs):
            return args, kwargs

        while True:
            yield nexter

            if method.upper() == 'GET':
                '''
                dispose GET method
                '''
                router = self.find_handler()()

                #router is response , we add the request attribute to the self instance

                # 1.the WrapperRequest object
                router.request = self.wrapper
                # 2. the global application instance binding here,this is an instance already
                router.app = self.wrapper.application

                nexter = getattr(router,'get')

            elif method.upper() == 'POST':
                '''
                handler POST method
                '''
                router = self.find_handler()()
                router.request = self.wrapper
                router.app = self.wrapper.application
                nexter = getattr(router, 'post')

            else:
                '''
                this means we don't handler except GET,POST, TODO and 
                robust web server.
                '''
                router = self.find_handler()()
                result = getattr(router, 'get')
                nexter = result

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
                if isinstance(result,types.MethodType):
                    return result
                elif isinstance(result,(str,bytes)):
                    body, status = result, 200
                elif isinstance(result,(tuple,list)) and len(result) == 2:
                    body, status = result[0], result[1]
                    assert isinstance(status,int) and  status in self.msg_pair.keys(), StatusError(status=status)
                else:
                    raise Exception('no handlering')

                '''
                for return result pretty only, never user json.dumps before , otherwise status is under prase
                too
                '''
                return json.dumps(body), status


    def gen_headers(self,version, status, msg, add_header=None):
        tmp = []
        '''
        return the headers that contains the response prefix
        '''

        self.headers['Server'] = " Pyweby Web 1.0"
        self.headers['first_line'] = "{version} {status} {msg}".format(version=version, status=status,msg=msg)

        if add_header and isinstance(add_header,dict):
            for k,b in add_header.items():
                if k not in self.headers.keys():
                    self.headers[k] = b

        if hasattr(self.wrapper,'_status_code') or hasattr(self.wrapper,'response_header'):

            self.headers.update(self.wrapper.response_header)
            status_code = self.wrapper._status_code
            self.headers['first_line'] = "{version} {status} {msg}".format(
                version=version,status=status_code or status, msg=self.msg_pair[status_code])

        # in Python3, ''.join(list) will raise `TypeError: sequence item 0: expected string, xx found`
        first_line = self.headers.pop('first_line')
        tmp.append(first_line)
        for pair in self.headers.items():
            tmp.append(': '.join(pair))

        header = '\r\n'.join(str(s) for s in tmp)
        return header + "\r\n\r\n"


    def gen_body(self,  prefix="\r\n\r\n", if_need_result = False):
        '''
        generator the body contains headers
        :param prefix: this prefix to tail whether the response package is integrity
        '''
        try:
            tmp = self.discern_result(time_consuming_op=self.switch_method(self.method))()
            if tmp is None:

                # You just need to generate a 302 hop and pass it to sock.
                response_for_no_return = self.gen_headers(self.version,None,None)
                return response_for_no_return

            body,status = tmp

        except Exception as e:
            self.Log.info(e)
            return self.not_future_body(500, 'internal server error', prefix=prefix)

        """
        8.10
        since from  switch_method getting called, the returning result can be
        an normal bytes? or string? type for return.
        but if you set concurrent generator a Future object 
        `<class 'concurrent.futures._base.Future'>` , so here you should judge
        Whether `body` is Future.tp_repr or not.
        ok_body is the method what you need?
        no, still call result(), blocking still, how can i solve it?
        
        8.14
        solution: using Observer-Model to delegate the Future and current socket
        to the EventMaster
        """
        if isinstance(body,_base.Future):
            # WE DON'T NEED if_need_result FLAG ANYMORE,CAUSE WE CAN JUDGE THE BRANCH TO GO BY
            # distinguish whether body is Future or (str,bytes...)
            self.ok_body(body)
        else:
            return self.not_future_body(status, body, prefix)


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
            return self.gen_headers(self.version, status, msg) + prefix + str(body)

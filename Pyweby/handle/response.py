import types
import json
import time

from handle.request import HttpRequest
from handle.exc import StatusError,MethodNotAllowedException
from concurrent.futures import _base, wait,ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION
from util.Observer import EventFuture,Eventer


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
        self.msg_pair = {200:'OK',
                         400:'METHOD NOT ALLOWED',
                         404:'NOT FOUND',
                         500:'SERVER ERROR'}
        # self.eventManager =

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
        '''
        return the headers that contains the response prefix
        '''
        header = u"{version} {status} {msg}\r\nServer: Pyweby Web 1.0".format(version=version,
                                                                                  status=status, msg=msg)
        if add_header and isinstance(header,dict):
            #TODO add header here
            pass

        return header

    def gen_body(self,  prefix='', if_need_result = False):
        '''
        generator the body contains headers
        :param prefix: this prefix to tail whether the response package is integrity
        '''
        try:
            instancemethod = self.discern_result(time_consuming_op=self.switch_method(self.method))
            body, status = instancemethod()
        except TypeError:
            body, status = self.discern_result(time_consuming_op=self.switch_method(self.method))
        except ValueError:
            #too many values to unpack (expected 2)
            return None

        '''
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
        '''

        if isinstance(body,_base.Future):
            # WE DON'T NEED if_need_result FLAG ANYMORE,CAUSE WE CAN JUDGE THE BRANCH TO GO BY
            # distinguish whether body is Future or (str,bytes...)
            self.ok_body(body)
        else:
            msg = self.msg_pair.get(status,200)
            if prefix != u'\r\n'*2:
                return json.dumps(body)
            else:
                return self.gen_headers(self.version, status, msg) + prefix + str(body)


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
            self.event_manager.addFuture(event)

        else:
            raise OSError("EventFuture must be new_class!")
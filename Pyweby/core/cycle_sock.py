#coding:utf-8
try:
    import queue as Queue #Python3
except ModuleNotFoundError:
    import Queue

import logging
import threading
import socket
import types
import time

from .sock import gen_serversock
from .config import Configs
from handle.request import WrapRequest,HttpRequest
from handle.response import WrapResponse
from handle.exc import NoRouterHandlers,FormatterError
from util.logger import Logger


class MainCycle(object):

    application = None
    '''
    do not add application in __init__, because in the subclass
    PollCycle, self.application will return the value is setted 
    None, so define application here in cls.
    '''

    def __init__(self):
        self._running = False

    @classmethod
    def checking_handlers(cls,handlers,conn):
        for uri, obj in handlers:
            assert callable(obj)
            # cls <class 'cycle_sock.PollCycle'>
            if isinstance(uri,(str,bytes)) and issubclass(obj,HttpRequest):
                continue
            else:
                raise FormatterError(uri=uri,obj=obj)



class PollCycle(MainCycle):

    '''
    MSG_QUEUE is aim for avoiding threading condition and simplify
    the threading.Lock acquire and release
    '''
    MSG_QUEUE = threading.local()
    MSG_QUEUE.pair = {}

    def __init__(self,*args,**kwargs):
        self._impl = kwargs.get('__impl',None)
        assert self._impl is not None

        self.timeout = kwargs.get('timeout',3600)
        self._thread_ident = threading.get_ident()

        self.handlers = self.trigger_handlers(kwargs)

        self.Log = Logger(logger_name=__name__)
        self.Log.setLevel(logging.INFO)

        super(PollCycle,self).__init__()

    def listen(self,port):
        self.server = gen_serversock(port)

        #AttributeError: 'SelectCycle' object has no attribute 'handlers'
        PollCycle.check(self.handlers, None)
        self.add_handler(self.server, Configs.M)

    @classmethod
    def check(cls,handlers,conn):

        if len(handlers) <= 0:
            raise NoRouterHandlers
        cls.checking_handlers(handlers,conn)

    @classmethod
    def consume(cls,message,debug=False):
        r = message
        while True:
            msg = yield r
            if debug:
                print("consume",msg)
            if not msg:
                return
            r = msg

    @classmethod
    def Coroutine(cls,gen, msg,debug=False):
        next(gen)
        if isinstance(gen,types.GeneratorType):
            while True:
                try:
                    result = gen.send(msg)
                    if debug:
                        print("coroutine",result)
                    gen.close()
                    return result
                except StopIteration:
                    return


    def server_forever(self,debug=False):

        while True:
            # this is blocking select.select io
            fd_event_pair = self._impl.sock_handlers(self.timeout)

            if debug:
                self.Log.info(fd_event_pair)
                time.sleep(1)

            for sock,event in fd_event_pair:
                if event & Configs.R:
                    if sock is self.server:

                        conn, address = sock.accept()

                        conn.setblocking(0)
                        '''
                        for convenience and no blocking program, we put the connection into inputs loop,
                        with the next cycling, this conn's fileno being ready condition, and can be append 
                        by readable list by select loops
                        '''

                        # trigger add_sock to change select.select(pool)'s pool, and change the listening
                        # event IO Pool
                        self._impl.add_sock(conn, Configs.R)
                        self.MSG_QUEUE.pair[conn] = Queue.Queue()

                    else:
                        try:
                            data = sock.recv(60000)
                            # self.Log.info(data)
                        except socket.error:
                            self.close(sock)
                            continue

                        '''
                        here is the request origin
                        PollCycle is origin from SelectCycle, application will be registered 
                        at there
                        '''
                        if self.application:

                            data = WrapRequest(data,lambda x:dict(x),handlers=self.handlers,
                                               application=self.application)

                        if data:
                            self.MSG_QUEUE.pair[sock].put(data)
                            self._impl.add_sock(sock,Configs.W)
                        # if there is no data receive, that means socket has been disconnected
                        else:
                            self.close(sock)

                elif event & Configs.W:
                    try:
                        msg = self.MSG_QUEUE.pair[sock].get_nowait()

                        writers = WrapResponse(msg)

                        body = writers.gen_body(prefix="\r\n\r\n")

                    except Queue.Empty:
                        self.close(sock)
                    else:
                        # for python3 reason, encode code for str2bytes
                        #here sock.send require bytes type , rather than string.
                        try:
                            bodys = body.encode()
                        except Exception:
                            bodys = body
                        finally:
                            sock.send(bodys)

                else:
                    self._impl.remove_sock(sock)
                    sock.close()

    def add_handler(self, fd, events):
        # fileno, fd = self.split_fd(fd)   #change to fileno
        # self._handlers[fd] = (obj, wrap(handler))
        self._impl.add_sock(fd, events)

    def split_fd(self, fd):
        try:
            return fd.fileno(), fd
        except AttributeError:
            return fd, fd

    def close(self,sock):
        self._impl.remove_sock(sock)
        sock.close()
        del self.MSG_QUEUE.pair[sock]
        # print self._impl._debug()

    def trigger_handlers(self,kw):
        raise NotImplementedError
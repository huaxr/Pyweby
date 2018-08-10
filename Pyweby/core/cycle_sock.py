#coding:utf-8
import Queue
import threading
import socket

import thread
import types

from sock import gen_serversock
from config import Configs
from handle.request import WrapRequest,HttpRequest
from handle.response import WrapResponse
from core.router import Router
from handle.exc import NoRouterHandlers,FormatterError

class MainCycle(object):

    def __init__(self):
        self._running = False

    @classmethod
    def checking_handlers(cls,handlers,conn):
        for uri, obj in handlers:
            assert callable(obj)
            # cls <class 'cycle_sock.PollCycle'>
            if isinstance(uri,(str,unicode,bytes)) and issubclass(obj,HttpRequest):
                continue
            else:
                raise FormatterError(uri=uri,obj=obj)

class PollCycle(MainCycle):
    msg_queue = threading.local()
    msg_queue.pair = {}

    def __init__(self,impl,timeout=3600,**kwargs):
        # super(PollCycle,self).__init__()
        self._impl = impl
        self.timeout = timeout
        self._thread_ident = thread.get_ident()
        self.server = gen_serversock()
        self.handlers = kwargs.get('handlers',[])
        PollCycle.check(self.handlers,None)
        self.add_handler(self.server,Configs.M)
        super(PollCycle,self).__init__()

    @classmethod
    def check(cls,handlers,conn):
        assert len(handlers) > 0, NoRouterHandlers
        cls.checking_handlers(handlers,conn)

    @classmethod
    def consume(cls,message,debug=False):
        r = message
        while True:
            msg = yield r
            if debug:
                print "consume",msg
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
                        print "coroutine",result
                    gen.close()
                    return result
                except StopIteration:
                    return


    def server_forever(self):
        while True:
            fd_event_pair = self._impl.sock_handlers(self.timeout)
            for sock,event in fd_event_pair:
                if event & Configs.R:
                    if sock is self.server:
                        conn, address = sock.accept()
                        conn.setblocking(False)
                        '''
                        for convenience and no blocking program, we put the connection into inputs loop,
                        with the next cycling, this conn's fileno being ready condition, and can be append 
                        by readable list by select loops
                        '''
                        self._impl.add_sock(conn, Configs.R)
                        self.msg_queue.pair[conn] = Queue.Queue()

                    else:
                        try:
                            data = sock.recv(60000)
                        except socket.error as e:
                            print e
                            self.close(sock)
                            continue

                        '''
                        here is the request origin
                        '''
                        # print data
                        data = WrapRequest(data,lambda x:dict(x),handlers=self.handlers,conn=sock)

                        if data:
                            self.msg_queue.pair[sock].put(data)
                            self._impl.add_sock(sock,Configs.W)
                        # if there is no data receive, that means socket has been disconnected
                        else:
                            self.close(sock)

                elif event & Configs.W:
                    try:
                        msg = self.msg_queue.pair[sock].get_nowait()
                        writers = WrapResponse(msg)
                        body = writers.gen_body("\r\n\r\n")

                    except Queue.Empty:
                        self.close(sock)
                    else:
                        sock.send(body)
                        # writers.send()

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
        del self.msg_queue.pair[sock]
        # print self._impl._debug()

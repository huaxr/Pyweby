# coding:utf-8
import ssl
import re
import threading
import socket
import types
import select

try:
    import queue as Queue
except ImportError:
    import Queue

from .ServerSock import gen_serversock, SSLSocket
from .config import Configs
from handle.request import WrapRequest, HttpRequest
from handle.response import WrapResponse
from handle.exc import NoRouterHandlers, FormatterError
from util.Engines import EventManager, _EventManager, EventResponse, EventFunc
from util.logger import init_loger, traceback
from util._compat import B_DCRLF, intern,PY2

Log = init_loger(__name__)


def thread_state(fn):
    def wrapper(self):
        if not (hasattr(self, 'eventManager') and hasattr(self, 'peventManager')):
            raise RuntimeError("Thread not started yet.")
        return fn

    return wrapper


class MainCycle(object):
    application = None
    '''
    do not add application in __init__, because in the subclass
    PollCycle, self.application will return the value is setted 
    None, so define application here in cls.
    '''

    def __init__(self, flag=False):
        self.flag = flag

    @classmethod
    def checking_handlers(cls, handlers, conn):
        for uri, obj in handlers:
            assert callable(obj)
            # cls <class 'cycle_sock.PollCycle'>
            if isinstance(uri, (str, bytes)) and issubclass(obj, HttpRequest):
                continue
            else:
                raise FormatterError(uri=uri, obj=obj)

    def ssl(self, wrapper):
        raise NotImplementedError


class MagicDict(dict):
    '''
    an dict support self-defined operator
    '''

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        self[attr] = value

    def __iadd__(self, rhs):
        self.update(rhs); return self

    def __add__(self, rhs):
        d = MagicDict(self);
        d.update(rhs);
        return d


class PollCycle(MainCycle, Configs.ChooseSelector):
    '''
    Threading. local () is a method that holds a global variable,
    but it is accessible only to the current thread
    '''
    pair = MagicDict()
    connection = MagicDict()

    def __init__(self, *args, **kwargs):

        self._impl = kwargs.get('__impl', None)
        assert self._impl is not None

        self.timeout = kwargs.get('timeout', 3600)
        # self._thread_ident = threading.get_ident()

        # the handlers of uri-obj pair . e.g. [('/',MainHandler),]
        # there is two ways to deliver the parameter
        # 1. using handler=[(),] directly
        # 2. using Configs.Application wrapper the handler in __init__
        # so, using trigger_handlers to get handlers for later usage.
        self.handlers = self.trigger_handlers(kwargs)

        # provides access to Transport Layer Security (often known as
        # “Secure Sockets Layer”) encryption and peer authentication
        # facilities for network sockets, both client-side and server-side
        self.ssl_options = kwargs.get('ssl_options', {})
        assert isinstance(self.ssl_options, dict)
        self.ssl_enable = self.ssl_options.get('ssl_enable', False)
        self.certfile = self.ssl_options.get('certfile', '')
        self.keyfile = self.ssl_options.get('keyfile', '')
        self.ssl_version = self.ssl_options.get('ssl_version', None)

        if self.ssl_enable and Configs.PY3:
            # self.context = ssl_context(self.ssl_options)
            self.context = ssl.SSLContext(self.ssl_version or Configs.V23)

            if any(len(x) <= 0 for x in [self.certfile,self.keyfile]):
                raise RuntimeError("[!] certfile,keyfile must defined when ssl enabled")
            self.context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        else:
            self.context = None

        '''
        enable EventManager, which means getting callback future
        to be achieve soon.
        self.queue if an Queue() for callback results.
        '''
        self.swich_eventmanager_on()

        self.__EPOLL = hasattr(select, 'epoll')
        self._re = re.compile(b'Content-Length: (.*?)\r\n')
        self.__re = re.compile(b'\r\n\r\n')
        self._POST = False
        self._GET = True

        '''
        self.middleware: this action function used to save the global request
        before and after it occurs, where the function pointer is saved for
        subsequent calls.
        '''
        setattr(self.application, 'request', self)
        self.middleware = MagicDict()

        for i in map(intern, ['__before__', '__after__']):
            self.middleware += {i: getattr(self.application, ''.join([i[2:-1], 'request']), None)}

        Configs.ChooseSelector.__init__(self, flag=self.__EPOLL)

    def swich_eventmanager_on(self):
        # starting the  eventManager._thread  for calling _run_events
        # and getting the events from the manager's Queue, if the Queue.get()
        # returns future object, means we catch the add_done_callback future
        # in finished. remember pass the sock obj for send result.

        # thread event manager. self.queue for callback result
        self.queue = Queue.Queue()
        self.eventManager = EventManager()
        self.peventManager = _EventManager(self.queue)

        for thread in [self.eventManager, self.peventManager]:
            thread.start()

    @thread_state
    def swich_eventmanager_off(self):
        # turning down/ shutting up
        for thread in [self.eventManager, self.peventManager]:
            print(thread)
            thread.stop()

    def listen(self, port=None):
        self.server = gen_serversock(port, ssl_enable=self.ssl_enable)
        PollCycle.check(self.handlers, None)
        self.add_handler(self.server, Configs.M)

    @classmethod
    def check(cls, handlers, conn):

        if len(handlers) <= 0:
            raise NoRouterHandlers
        cls.checking_handlers(handlers, conn)

    @classmethod
    def consume(cls, message, debug=False):
        r = message
        while True:
            msg = yield r
            if debug:
                print("consume", msg)
            if not msg:
                return
            r = msg

    @classmethod
    def Coroutine(cls, gen, msg, debug=False):
        next(gen)
        if isinstance(gen, types.GeneratorType):
            while True:
                try:
                    result = gen.send(msg)
                    if debug:
                        print("coroutine", result)
                    gen.close()
                    return result
                except StopIteration:
                    return

    def server_forever_select(self, debug=False):
        # this is blocking select.select io
        while True:
            try:
                # there may some sockets means Exception and close by self,
                # so we should pass it checking
                fd_event_pair = self._impl.sock_handlers(self.timeout)
            except OSError as e:
                Log.info(traceback(e, "error"))
                continue

            except KeyboardInterrupt:
                self.server.close()
                break

            for sock, event in fd_event_pair:
                if event & Configs.R:
                    if sock is self.server:
                        conn, address = sock.accept()
                        # if using ssl
                        # ValueError: do_handshake_on_connect should not be specified for non-blocking sockets
                        # so disable non-blocking here and enable it after wrap the sock.
                        # conn.setblocking(0)

                        # just wrapped the conn-sock , socket-type to SSLSocket type
                        try:
                            with SSLSocket(self.context, conn, self.certfile, self.keyfile) as ssl_wrapper:
                                conn = self.ssl(ssl_wrapper)
                                conn.setblocking(0)

                        except (ssl.SSLError, OSError) as e:
                            Log.info(traceback(e))
                            self.close(conn)
                            continue

                        else:
                            '''
                            for convenience and no blocking program, we put the connection into inputs loop,
                            with the next cycling, this conn's fileno being ready condition, and can be append 
                            by readable list by select loops
                            '''
                            # trigger add_sock to change select.select(pool)'s pool, and change the listening event IO Pool
                            self._impl.add_sock(conn, Configs.R)
                            # define the sock:Queue pair for message
                            self.pair[conn] = Queue.Queue()

                    else:
                        if sock.fileno() != -1:
                            # Due to active or passive reasons, socket shutdown is not processed in time,
                            # and it is necessary to determine whether socket is closed.
                            # data_ = PollCycle.blocking_recv(self,sock)
                            # data = b''.join(data_)
                            event = EventFunc(PollCycle.blocking_recv, self, sock)
                            self.peventManager.addEvent(event)
                            '''
                            here is the request origin.
                            PollCycle is origin from SelectCycle, application will be registered 
                            at there

                            the define of the main.py has two ways:
                            1. server = loop(handlers=[(r'/hello',testRouter2),])
                            2. server = loop(Barrel) 

                            if 2 is choosen to be the method, with a series of examinations,
                            self.application will be set the Barrel instance

                            '''
                            # callback result from _EventMaster.
                            try:
                                data = self.queue.get()
                            except Queue.Empty:
                                continue

                            if data:
                                # mark here for execute global_before_request
                                _kw = self.before_request()

                                data = WrapRequest(data, lambda x: dict(x), handlers=self.handlers,
                                                   application=self.application, sock=sock, **_kw)
                                # for later usage, when the next Loop by the kernel select, that's
                                # will be reuse the data putting in it.
                                if sock in self.pair:
                                    self.pair[sock].put(data)
                                    self._impl.add_sock(sock, Configs.W)

                            else:
                                # if there is no data receive, that means socket has been disconnected
                                # so , let's remove it now!
                                self.close(sock)

                elif event & Configs.W:
                    try:
                        if sock in self.pair:
                            msg = self.pair[sock].get_nowait()
                        else:
                            continue

                    except Queue.Empty:
                        pass

                    else:
                        # consider future.result() calling and non-blocking , we should
                        # activate the EventManager, and trigger sock.send() later in the
                        # EventManager sub threads Looping.
                        writers = WrapResponse(msg, self.eventManager, sock, self, **self.middleware)
                        event = EventResponse(writers)
                        self.eventManager.addRequestWrapper(event)

                else:
                    Log.info(traceback("other reason, close sock", "error"))
                    self.close(sock)

    def server_forever_epoll(self, debug=False, timeout=-1):
        '''
        Enhance the performance of IO loop.
        Using epoll first if condition promise.
        STEPS:
        1. Create an epoll object
        2. Tell the epoll object to monitor specific events on specific sockets
        3. Ask the epoll object which sockets may have had the specified event since the last query
        4. Perform some action on those sockets
        5. Tell the epoll object to modify the list of sockets and/or events to monitor
        6. Repeat steps 3 through 5 until finished
        7. Destroy the epoll object
        '''
        while 1:
            events = self._impl.poll(timeout)

            if not events:
                Log.info("Epoll timeout, continue roll poling.")
                continue

            if debug:
                Log.info("there are %d events prepare to handling." % len(events))

            for fileno, event in events:
                # If active socket is the current server socket, represent that is a new connection.
                # self.server if registered by listen method
                if fileno == self.server.fileno():
                    conn, addr = self.server.accept()

                    try:
                        with SSLSocket(self.context, conn, self.certfile, self.keyfile) as ssl_wrapper:
                            conn = self.ssl(ssl_wrapper)
                            conn.setblocking(0)

                    except (ssl.SSLError, OSError) as e:
                        Log.info(traceback(e))
                        self.close(conn)
                        continue

                    # Register new connection fileno to read event collection

                    self._impl.register(conn.fileno(), select.EPOLLIN)
                    self.connection[conn.fileno()] = conn
                    self.pair[conn.fileno()] = Queue.Queue()

                # Readable Rvent
                # select.EPOLLIN == 1, if event =1, than & operation will return 1.
                # trigger the event handler.
                elif event & select.EPOLLIN:
                    sock = self.connection.get(fileno, None)
                    if sock is None or sock.fileno() == -1:
                        continue

                    # try:
                    #     data = sock.recv(6000)
                    # except Exception as e:
                    #     Log.info(traceback(e))
                    #     self.eclose(fileno)
                    #     continue
                    event = EventFunc(PollCycle.blocking_recv, self, sock)
                    self.peventManager.addEvent(event)

                    try:
                        data = self.queue.get()
                    except Queue.Empty:
                        continue

                    # now on wrapper the request

                    if data:

                        _kw = self.before_request()

                        data = WrapRequest(data, lambda x: dict(x), handlers=self.handlers,
                                           application=self.application, sock=sock, **_kw)

                        if fileno in self.pair:
                            # manually modify socket status in epoll.
                            # this is the core epoll IO mechanism.
                            self.pair[fileno].put(data)
                            self._impl.modify(fileno, select.EPOLLOUT)
                        else:
                            # that's means some error happens and eclose
                            # called but not notify yet.
                            continue

                    else:
                        self.eclose(fileno)

                # Writeable Event
                elif event & select.EPOLLOUT:
                    sock = self.connection.get(fileno, None)
                    if sock is None or sock.fileno() == -1:
                        continue
                    try:
                        if fileno in self.pair:
                            msg = self.pair[fileno].get_nowait()
                        else:
                            continue

                    except Queue.Empty:
                        # core reason, savvy?
                        self._impl.modify(fileno, select.EPOLLIN)
                    else:
                        '''
                        writers = WrapResponse(msg, self.eventManager, sock, self)
                        body = writers.gen_body(prefix="\r\n\r\n")
                        if body:
                            try:
                                bodys = body.encode()
                            except Exception:
                                bodys = body

                            sock.send(bodys)
                            self.eclose(fileno)
                        else:
                            continue
                        '''
                        writers = WrapResponse(msg, self.eventManager, sock, self, **self.middleware)
                        event = EventResponse(writers)
                        self.eventManager.addRequestWrapper(event)


                # Close Event
                elif event & select.EPOLLHUP:
                    if debug:
                        Log.info("Closing event,%d" % fileno)

                    self.eclose(fileno)

                else:
                    continue

    def add_handler(self, fd, events):
        '''
        register sock fileno:events pair
        '''
        if self.__EPOLL:
            self._impl.register(fd, select.EPOLLIN)  # read
        else:
            self._impl.add_sock(fd, events)

    def modify(self, sock):
        self._impl.modify_sock(sock, Configs.W)

    def close(self, sock):
        # assert isinstance(sock,socket.socket)
        self._impl.remove_sock(sock)
        if PY2:
            # reference Google solves the problem that SSL socket reception can not be returned
            # in python2 environment.
            sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        '''
        threading.local declare:
        if the close function is not called from the main-thread, self.MSG_QUEUE.pair will
        not be existed! because the sub thread and main thread is not have the condition
        to operate both threading.local variable.
        so, if EventMaster's sub thread called this method, when calling 
        >>> self.MSG_QUEUE.pair 
        that will raise Error like below:
        `AttributeError: '_thread._local' object has no attribute 'pair'`

        so, here we can't use local() 
        '''
        # TODO
        if sock in self.pair:
            self.pair.pop(sock)

    def eclose(self, fd):
        '''
        a collection operators for closing an socket from the poll
        and the defined variable from this sock.
        which is only used in epoll looper
        '''
        try:
            self._impl.unregister(fd)
            sock = self.connection.pop(fd)
            if PY2:
                # reference Google solves the problem that SSL socket reception can not be returned
                # in python2 environment.
                sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            self.pair.pop(fd)
        except Exception:
            pass

    def trigger_handlers(self, kw):
        '''
        to generate handlers pairs.
        find_router will call this to distribute an request handler.
        '''
        raise NotImplementedError


    def ssl(self, wrapper):
        '''
        To support ssl, you need to make ssl-context, which is used
        to wrap sockets so that their certificate and private keys are valid
        on the context wrapper.

        this is an interface for implementing wrapper to ssl-context.
        '''
        if self.ssl_enable:
            return wrapper.ssl_context()

        else:
            return wrapper.conn

    @classmethod
    def blocking_recv(cls, self, sock):
        sock.settimeout(5)
        data_ = []
        length = 0
        pos = 0
        while 1:
            try:
                data = sock.recv(65535)
            except (socket.error, Exception) as e:
                Log.info(traceback(e))
                self.close(sock)
                break  # turn continue to break. or will drop-dead halt

            if data.startswith(b'GET'):
                if data.endswith(B_DCRLF):
                    data_.append(data)
                    break
                else:
                    data_.append(data)

            elif data.startswith(b'POST'):
                # TODO, blocking recv , how to solving.
                # server side uploading .
                sock.setblocking(1)
                length = int(self._re.findall(data)[0].decode())
                header_part, part_part = self.__re.split(data, 1)

                data_.extend([header_part, B_DCRLF, part_part])
                pos = len(part_part)
                self._POST = True


            elif data.startswith(b'PUT'):
                pass

            elif data.startswith(b'OPTIONS'):
                pass

            elif data.startswith(b'HEAD'):
                pass

            elif data.startswith(b'DELETE'):
                pass

            if self._POST:
                if length <= pos:
                    if data and not data.startswith(b'POST'):
                        # always put the last pieces of raw data in the list
                        # otherwise, the data will be incomplete and the file
                        # will fail.
                        # after this, break while, recv complete.
                        data_.append(data)
                    break
                else:
                    if data and not data.startswith(b'POST'):
                        data_.append(data)
                        pos += len(data)
        return b''.join(data_)


    def before_request(self):
        _kw = {}
        _before_func = self.middleware.get('__before__')
        if _before_func:
            _kw['before'] = _before_func()
        return _kw
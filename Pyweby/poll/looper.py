# coding:utf-8
import ssl
import re
import socket
import types
import select

from core.server_sock import gen_socket, SSLSocket
from handle.request import WrapRequest, HttpRequest
from handle.response import WrapResponse
from exceptions.exc import NoRouterHandlers, FormatterError
from util.Engines import EventManager, _EventManager, EventResponse, EventFunc
from log.logger import init_loger, traceback
from compat.compat import intern, PY2
from config.dic import MagicDict
from config.config import Configs
from .check import ChooseSelector
from poll.sock.read import blocking_recv

try:
    import queue as Queue
except ImportError:
    import Queue

Log = init_loger(__name__)

def thread_state(fn):
    def wrapper(self):
        if not (hasattr(self, 'eventManager') and hasattr(self, 'peventManager')):
            raise RuntimeError("Thread not started yet.")
        return fn

    return wrapper



class PollCycle(ChooseSelector):
    pair = MagicDict()
    connection = MagicDict()

    def __init__(self, *args, **kwargs):
        self._impl = kwargs.get('__impl', None)
        assert self._impl is not None
        self.timeout = kwargs.get('timeout', 3600)
        # the handlers of uri-obj pair . e.g. [('/',MainHandler),]
        # there is two ways to deliver the parameter
        # 1. using handler=[(),] directly
        # 2. using Application wrapper the handler in __init__
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
            if any(len(x) <= 0 for x in [self.certfile, self.keyfile]):
                raise RuntimeError("[!] certfile,keyfile must defined when ssl enabled")
            self.context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        else:
            self.context = None
        # enable EventManager, which means getting callback future
        # to be achieve soon.
        # self.queue if an Queue() for callback results.
        self.swich_eventmanager_on()
        self.__EPOLL = "EPOLL" if hasattr(select, 'epoll') else ""
        self.__KQUEUE = "KQUEUE" if hasattr(select, 'kqueue') else ""
        self.__FLAG = self.__EPOLL or self.__KQUEUE or "SELECT"

        self._re = re.compile(b'Content-Length: (.*?)\r\n')
        self.__re = re.compile(b'\r\n\r\n')
        self._POST = False
        self._GET = True
        # self.middleware: this action function used to save the global request
        # before and after it occurs, where the function pointer is saved for
        # subsequent calls.
        setattr(self.application, 'request', self)
        self.middleware = MagicDict()

        for i in map(intern, ['__before__', '__after__']):
            self.middleware += {i: getattr(self.application, ''.join([i[2:-1], 'request']), None)}
        ChooseSelector.__init__(self, flag=self.__FLAG)

    def swich_eventmanager_on(self):
        """
        starting the  eventManager._thread  for calling _run_events
        and getting the events from the manager's Queue, if the Queue.get()
        returns future object, means we catch the add_done_callback future
        in finished. remember pass the sock obj for send result.

        thread event manager. self.queue for callback result
        """
        self.queue = Queue.Queue()
        self.eventManager = EventManager()
        self.peventManager = _EventManager(self.queue)
        for thread in [self.eventManager, self.peventManager]:
            thread.start()

    @thread_state
    def swich_eventmanager_off(self):
        """
        turning down/shutting up
        """
        for thread in [self.eventManager, self.peventManager]:
            print(thread)
            thread.stop()

    def listen(self, port=None):
        """
        listen options register the server socket in the select looper.
        on linux, windows. For Mac OS, it's not initilize.
        """
        self.server = gen_socket(port, ssl_enable=self.ssl_enable)
        self.check_handlers(self.handlers)
        self.add_handler(self.server, Configs.M)

    def check_handlers(self, handlers):
        if len(handlers) <= 0:
            raise NoRouterHandlers
        for uri, obj in handlers:
            assert callable(obj)
            if isinstance(uri, (str, bytes)) and issubclass(obj, HttpRequest):
                continue
            else:
                raise FormatterError(uri=uri, obj=obj)

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

                            # trigger add_sock to change select.select(pool)'s pool, and change the listening event
                            # IO Pool
                            self._impl.add_sock(conn, Configs.R)
                            # define the sock:Queue pair for message
                            self.pair[conn] = Queue.Queue()

                    #   elif sock is sys.stdin:
                    #       Log.info("Not handler stdin inputs!")

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

                                data_ = WrapRequest(data, lambda x: dict(x), handlers=self.handlers,
                                                    application=self.application, sock=sock, **_kw)
                                # for later usage, when the next Loop by the kernel select, that's
                                # will be reuse the data putting in it.
                                if sock in self.pair:
                                    self.pair[sock].put(data_)
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

    def server_forever_kqueue(self, debug=False):
        """
        (Only supported on BSD.)
        Returns a kernel event object;
        For BSD or Mac os. kevent is first consider to become the IO Loop for
        these operation system.
        easy achievement.
        """
        # generate kevent list for socket reading operation
        kevents = [select.kevent(self.server.fileno(), filter=select.KQ_FILTER_READ, flags=select.KQ_EV_ADD), ]
        while 1:
            # doc file : https://docs.python.org/3/library/select.html#kqueue-objects
            try:
                # starting kqueue, if there has executable kevent, return the kevent-list directly
                eventlist = self._impl.control(kevents, 10, 10)
            except select.error as e:
                print(e)
                break

            if eventlist:
                for event in eventlist:
                    if event.ident == self.server.fileno():
                        conn, _ = self.server.accept()
                        try:
                            with SSLSocket(self.context, conn, self.certfile, self.keyfile) as ssl_wrapper:
                                conn = self.ssl(ssl_wrapper)
                        except (ssl.SSLError, OSError) as e:
                            Log.info(traceback(e))
                            self.close(conn)
                            continue
                        conn.setblocking(0)
                        self.connection[conn.fileno()] = conn
                        kevents.append(select.kevent(conn.fileno(), select.KQ_FILTER_READ, select.KQ_EV_ADD, udata=conn.fileno()))
                    else:
                        # if not socket connect, than get the connection and doing write operation on it!
                        if event.udata >= 1 and event.flags == select.KQ_EV_ADD and event.filter == select.KQ_FILTER_READ:
                            conn = self.connection[event.udata]
                            data = blocking_recv(self, conn, timeout=20)
                            if data:
                                _kw = self.before_request()
                                data_ = WrapRequest(data, lambda x: dict(x), handlers=self.handlers,
                                            application=self.application, sock=conn, **_kw)
                                writers = WrapResponse(data_, self.eventManager, conn, self, **self.middleware)
                                events = EventResponse(writers)
                                self.eventManager.addRequestWrapper(events)  # called kclose already. just release kevents.

                                try:
                                    kevents.remove(select.kevent(self.connection[event.udata].fileno(), select.KQ_FILTER_READ,
                                                            select.KQ_EV_ADD, udata=event.udata))
                                except ValueError:
                                    pass

                                if event.data in self.connection:
                                    del self.connection[event.udata]

    def add_handler(self, fd, events):
        '''
        register sock fileno:events pair
        '''
        if self.__EPOLL:
            self._impl.register(fd, select.EPOLLIN)  # read

        elif self.__KQUEUE:
            # here we dont's achieve the register method.
            pass
        else:
            self._impl.add_sock(fd, events)

    def modify(self, sock):
        self._impl.modify_sock(sock, Configs.W)

    def close(self, sock, keepalive=False):
        self._impl.remove_sock(sock)
        if PY2:
            # reference Google solves the problem that SSL socket reception can not be returned in python2 environment.
            '''
            Shut down one or both halves of the connection. 
            1. If how is SHUT_RD, further receives are disallowed. 
            2. If how is SHUT_WR, further sends are disallowed. 
            3. If how is SHUT_RDWR, further sends and receives are disallowed. 
            Depending on the platform, shutting down one half of the connection can also close the opposite half 
            (e.g. on Mac OS X, shutdown(SHUT_WR) does not allow further reads on the other end of the connection).
            '''
            sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        if sock in self.pair:
            self.pair.pop(sock)

    def eclose(self, fd, keepalive=False):
        '''
        a collection operators for closing an socket from the poll
        and the defined variable from this sock.
        which is only used in epoll looper
        '''

        # if keep alive was set
        if keepalive:
            self._impl.modify(fd, select.EPOLLIN)

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

    def kclose(self, sock, keepalive=False):
        sock.close()

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

    def before_request(self):
        _kw = {}
        _before_func = self.middleware.get('__before__')
        if _before_func:
            _kw['before'] = _before_func()
        return _kw

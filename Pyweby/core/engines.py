# encoding: UTF-8
import types
import re
import select
import threading
from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor
from common.logger import init_loger, traceback

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

Log = init_loger(__name__)

__all__ = ('EventManager', 'Event', 'EventFuture')



class Switcher(object):
    '''
    just play the part of a switch which control EventManager start or stop.
    '''

    def __init__(self, active, thread):
        self._active = active
        self._thread = thread

    def stop(self):
        # stopping
        self._active = False
        self._thread.join()

    def start(self):
        # active EventManager
        self._active = True
        # active event handling thread
        self._thread.start()


class _Process(Process):
    def __init__(self, target=None):
        Process.__init__(self)
        self.target = target

    def run(self):
        self.target()


class _EventManager(Switcher):
    def __init__(self, q):
        self._eventQ = Queue()
        self.callback_queue = q
        self._active = False
        self._thread = threading.Thread(target=self._run_events)

        self._re = re.compile(b'Content-Length: (.*?)\r\n')
        self.__re = re.compile(b'\r\n\r\n')
        super(_EventManager, self).__init__(self._active, self._thread)

    def _run_events(self):
        while self._active == True:
            try:
                # The blocking time of the event is set to 1 second.
                event = self._eventQ.get(block=True, timeout=1)
                if isinstance(event, EventFunc):
                    result = self.eventFunc(event)
                    self.callback_queue.put(result)
                    continue
            except Empty:
                pass

    def eventFunc(self, event):
        func = event.func
        selfer = event.selfer
        sock = event.sock
        if sock.fileno() != -1:
            return func(selfer, sock)

    def addEvent(self, event):
        self._eventQ.put(event)


class EventManager(Switcher):
    def __init__(self):
        """
        initialize the manager event handler
        """
        # The Queue list object of event-obj
        self._eventQ = Queue()
        # the switcher of the event-manager
        self._active = False
        # the thread for handling the events, witch generate from EventManager object
        self._thread = threading.Thread(target=self._run_events)
        self.__EPOLL = hasattr(select, 'epoll')
        self.__KQUEUE = hasattr(select, 'kqueue')
        '''
        The __handlers here is a dict() that stores the 
        corresponding response functions of events.
        Each of these keys corresponds to a list of one-to-many 
        response functions that hold listeners for the event
        '''
        self._handlers = {}
        super(EventManager, self).__init__(self._active, self._thread)

    def _run_events(self):
        while self._active is True:
            try:
                # The blocking time of the event is set to 1 second.
                event = self._eventQ.get(block=True, timeout=1)
                # concurrent thread enable. 8.26
                if isinstance(event, EventResponse):
                    self._responseProcess(event)

                elif isinstance(event, EventFuture):
                    self._futureProcess(event)

                elif isinstance(event, Event):
                    self._EventProcess(event)

                else:
                    continue

            except Empty:
                pass

    def _futureProcess(self, event):
        sock = event.sock
        future = event.future
        pollcycle = event.PollCycle
        headers = event.headers

        response = headers + str(future.result())
        try:
            if sock.fileno() > 0:
                sock.sendall(response.encode())

        except (OSError, Exception) as e:
            '''
            when calling sock.send, you must verify that the socket is not
            closed yet, if that happens, will raise OSError so will ignore
            it means op system has invoke GC for us. 
            '''
            Log.info(traceback(e))

        finally:
            if self.__EPOLL:
                pollcycle.eclose(sock.fileno())
            elif self.__KQUEUE:
                pollcycle.kclose(sock)
            else:
                pollcycle.close(sock)

    def _responseProcess(self, event):
        # msg = event.request_wrapper
        # eventManager = event.event_manager
        # sock = event.sock
        # PollCycle = event.PollCycle
        # writers = WrapResponse(msg,eventManager,sock,PollCycle)
        writers = event.writers
        # keeping alive and don't close sock
        keepalive = writers.wrapper.keepalive
        sock = writers.sock
        PollCycle = writers.PollCycle

        body = writers.gen_body(prefix="\r\n\r\n")

        if body:
            try:
                bodys = body.encode()
            except Exception:
                bodys = body

            # employ curl could't deal with 302
            # you should try firefox or chrome instead
            sock.sendall(bodys)
            # when requst finished , the sock send all the msg.
            # call after_request.

            after_request = writers.kwargs.get('__after__', None)
            if after_request:
                after_request()

            # do not call sock.close, because the sock still in the select,
            # for the next loop, it will raise ValueEror `fd must not -1`
            if self.__EPOLL:
                PollCycle.eclose(sock.fileno(), keepalive=keepalive)

            elif self.__KQUEUE:
                PollCycle.kclose(sock, keepalive=keepalive)

            else:
                PollCycle.close(sock, keepalive=keepalive)

        else:
            '''
            Question: maybe body is None, just close it means connection terminate.
            and client will receive `Empty reply from server`?

            Answer:  No. if exception happens, or Future is waiting for 
            the result() in the EventMaster, if you close the sock, you
            will never send back message from the future!
            Keep an eye on it!
            '''
            # self.Log.info(body)
            # self.close(sock)
            # we can't set None to it
            pass

    def _EventProcess(self, event):
        """handle the event"""
        # check if there is the handler key
        if event.type in self._handlers:
            # handling events
            with ThreadPoolExecutor() as pool:
                for handler in self._handlers[event.type]:
                    future = pool.submit(handler, event)
                    future.add_done_callback(self.task_done)

    def task_done(self, finish_future):
        self._eventQ.put((finish_future))

    def addEventListener(self, event_type, handler):  # 'future',finished_future
        """
        Binding events and listener processing functions
        """
        try:
            handlerList = self._handlers[event_type]
        except KeyError:
            handlerList = []

        self._handlers[event_type] = handlerList
        # do register if handle not exists
        if handler not in handlerList:
            handlerList.append(handler)

    def deleteEventListener(self, event_type, handler):
        """remove handler"""
        pass

    def addEvent(self, normal_event):
        """putting event on the queue"""
        self._eventQ.put(normal_event)

    def addFuture(self, future_event):
        """async future handler"""
        self._eventQ.put(future_event)

    def addRequestWrapper(self, wrapper_event):
        """async response handler"""
        self._eventQ.put(wrapper_event)


class Eventer(object):
    '''
    descriptor for the event's subclasses
    '''

    def __init__(self):
        pass

    def __repr__(self):
        return 'Pyweby Event master'

    def __reduce__(self):
        return 'Event Master'


class Event(Eventer):
    def __init__(self, _type=None):
        self.type = _type
        self.dict = {}
        super(Event, self).__init__()


class EventFuture(Eventer):
    '''
    event object, you can define any events here like the.
    and than calling EventManager.addFuture or addEvent to
    register the type of events
    '''
    def __init__(self, future=None, _sock=None, _PollCycle=None, headers=None):
        self.future = future
        self.sock = _sock
        self.PollCycle = _PollCycle
        self.headers = headers
        self.dict = {}
        super(EventFuture, self).__init__()


class EventResponse(Eventer):
    def __init__(self, writers):  # msg,event_manager,sock,_PollCycle=None):
        # self.request_wrapper = msg
        # self.event_manager = event_manager
        # self.sock = sock
        # self.PollCycle = _PollCycle
        self.writers = writers
        super(EventResponse, self).__init__()


class EventRecv(Eventer):
    def __init__(self, sock=None, _impl=None, pair=None, PollCycle=None, WrapRequest=None, handlers=None,
                 application=None):
        self.sock = sock
        self._impl = _impl
        self.pair = pair
        self.PollCycle = PollCycle
        self.WrapRequest = WrapRequest
        self.handlers = handlers
        self.application = application
        super(EventRecv, self).__init__()


class EventFunc(Eventer):
    def __init__(self, func=None, selfer=None, sock=None):
        self.func = func
        self.selfer = selfer
        self.sock = sock
        super(EventFunc, self).__init__()
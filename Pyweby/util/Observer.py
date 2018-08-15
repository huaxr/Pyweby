# encoding: UTF-8
from concurrent.futures import ThreadPoolExecutor,_base
import time

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

from threading import Thread,Timer


__all__ = ('EventManager','Event','EventFuture')

class Eventer(object):
    '''
    descriptor for the event's subclasses
    '''
    def __init__(self):
        pass
    pass

class Switcher(object):
    '''
    just play the part of a switch which control EventManager start or stop.
    '''
    def __init__(self,active,thread):
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
        self._thread = Thread(target = self._run_events)

        '''
        The __handlers here is a dict() that stores the 
        corresponding response functions of events.
        Each of these keys corresponds to a list of one-to-many 
        response functions that hold listeners for the event
        '''
        self._handlers = {}
        super(EventManager,self).__init__(self._active,self._thread)

    def _run_events(self):
        while self._active == True:
            try:
                # The blocking time of the event is set to 1 second.
                event = self._eventQ.get(block = True, timeout = 1)
                if isinstance(event,EventFuture):
                    self._futureProcess(event)
                elif isinstance(event,Event):
                    self._EventProcess(event)
                else:
                    continue
            except Empty:
                pass


    def _futureProcess(self,event):
        try:
            event.sock.send(event.future.result().encode())
        except OSError:
            '''
            when calling sock.send, you must verify that the socket is not
            closed yet, if that happens, will raise OSError so will ignore
            it means op system has invoke GC for us. 
            '''
            pass
        # prevent select loop FULL
        event.PollCycle.close(event.sock)
        # event.sock.close()

    def _EventProcess(self, event):
        """handle the event"""
        # check if there is the handler key
        if event.type in self._handlers:
            # handling events
            with ThreadPoolExecutor() as pool:
                for handler in self._handlers[event.type]:
                    future = pool.submit(handler, event)
                    future.add_done_callback(self.task_done)

    def task_done(self,finish_future):
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

    def addFuture(self,future_event):
        self._eventQ.put(future_event)


class Event(Eventer):
    def __init__(self, _type=None):
        self.type = _type
        self.dict = {}
        super(Event,self).__init__()

class EventFuture(Eventer):
    '''
    event object, you can define any events here like the.
    and than calling EventManager.addFuture or addEvent to
    register the type of events
    '''
    def __init__(self, future=None,_sock=None,_PollCycle=None):
        self.future = future
        self.sock = _sock
        self.PollCycle = _PollCycle
        self.dict = {}
        super(EventFuture, self).__init__()

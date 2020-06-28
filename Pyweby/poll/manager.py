#coding: utf-8

from core.engines import EventManager, _EventManager
from common.wrapper import thread_state
try:
    import queue as Queue
except ImportError:
    import Queue

class Manager(object):
    def switch_manager_on(self):
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
    def switch_manager_off(self):
        """
        turning down/shutting up
        """
        for thread in [self.eventManager, self.peventManager]:
            print(thread)
            thread.stop()
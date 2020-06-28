# coding:utf-8
from core.server_sock import gen_socket
from core.engines import EventManager, _EventManager
from common.wrapper import thread_state
from config.dic import MagicDict
from config.config import Configs
from .check import BarrelCheck
from poll.runner import RunSelectLoop
try:
    import queue as Queue
except ImportError:
    import Queue


class PollCycle(RunSelectLoop):
    def __init__(self, *args, **kwargs):
        self.init_impl(kwargs)
        # the handlers of uri-obj pair . e.g. [('/',MainHandler),]
        # there is two ways to deliver the parameter
        # 1. using handler=[(),] directly
        # 2. using Application wrapper the handler in __init__
        # so, using trigger_handlers to get handlers for later usage.
        self.handlers = self.trigger_handlers(kwargs)
        # provides access to Transport Layer Security (often known as
        # “Secure Sockets Layer”) encryption and peer authentication
        # facilities for network sockets, both client-side and server-side
        self.init_ssl_context(**kwargs)
        # enable EventManager, which means getting callback future
        # to be achieve soon.
        # self.queue if an Queue() for callback results.
        self.switch_manager_on()
        # self.middleware: this action function used to save the global request
        # before and after it occurs, where the function pointer is saved for
        # subsequent calls.
        self.init_middleware()
        setattr(self.application, 'request', self)
        RunSelectLoop.__init__(self, kwargs)

    def listen(self, port=None):
        """
        listen options register the server socket in the select looper.
        on linux, windows. For Mac OS, it's not initilize.
        """
        self.server = gen_socket(port, ssl_enable=self.ssl_enable)
        BarrelCheck.check_handlers(self.handlers)
        self.add_handler(self.server, Configs.M)

    def trigger_handlers(self, kw):
        '''
        to generate handlers pairs.
        find_router will call this to distribute an request handler.
        '''
        raise NotImplementedError

# coding:utf-8
from core.server_sock import gen_socket
from common.config import Configs
from poll.check import BarrelCheck
from poll.runner import RunSelectLoop
from common.compat import SLASH
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

    def trigger_handlers(self,kw):
        '''
        this method for layout the handlers user define in the main.py.
        if user pass an object inherit Application, that means
        self has been set application parameter, which is the Application
        user defines, has many useful attribute for later calling.
        :param kw:  passed form the super class, has been wrapped
        :return: the handlers property. defined in main.py which is subclass
            of HttpRequest and added into the handlers key-value pair
        '''
        app = self.application
        if app:
            handlers = []
            tmp =  app.handlers
            for i,j in tmp:
                if i.startswith(SLASH):
                    pass
                else:
                    i = SLASH + i
                handlers.append((i,j))

            prefix = app.settings.get('uri_prefix',None)

            if prefix:
                if prefix.startswith(SLASH):
                    pass
                else:
                    prefix = SLASH + prefix
                mapper = map(lambda i: (prefix + i[0], i[1]), handlers)
                if isinstance(mapper, map):
                    return list(mapper)
                return mapper
            return handlers
        return kw.get('handlers',[])



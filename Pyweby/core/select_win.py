import select
from cycle_sock import PollCycle
from config import Configs

class _select(object):
    def __init__(self):
        self.read_fds =  set()
        self.write_fds = set()
        self.error_fds = set()
        # self.fd_sets = (self.read_fds, self.write_fds, self.error_fds)

    def _debug(self):
        return [len(x) for x in self.read_fds,self.write_fds,self.error_fds]

    def sock_handlers(self,timeout):
        readable, writeable, exceptions = select.select(self.read_fds, self.write_fds, self.error_fds, timeout)
        events = {}   #{fd:event}
        for fd in readable:
            events[fd] = events.get(fd, 0) | Configs.R
        for fd in writeable:
            events[fd] = events.get(fd, 0) | Configs.W
        for fd in exceptions:
            events[fd] = events.get(fd, 0) | Configs.E
        return events.items()

    def add_sock(self,fd, event):
        # if fd in self.read_fds or fd in self.write_fds or fd in self.error_fds:
        #     raise IOError("fd %s already registered" % fd)
        if event & Configs.R:     # only if equal than return 1
            self.read_fds.add(fd)
        if event & Configs.W:
            self.write_fds.add(fd)
        if event & Configs.E:
            self.error_fds.add(fd)
        # if event & Configs.M:  # for main socket only
        #     self.read_fds.add(fd)
        #     self.write_fds.add(fd)
        #     self.error_fds.add(fd)


    def remove_sock(self,fd):
        self.read_fds.discard(fd)
        self.write_fds.discard(fd)
        self.error_fds.discard(fd)

    def modify_sock(self,fd,event):
        self.remove_sock(fd)
        self.add_sock(fd, event)

    def close(self):
        raise NotImplementedError

class SelectCycle(PollCycle,Configs.BarrelCheck):

    def __init__(self,*args, **kwargs):
        '''
        this is the main loop started place
        '''
        self.application = None

        flag, obj = self.if_define_barrel(args,kwargs)
        if flag and obj:
            self.wrapper_barrel(obj,kwargs)

        kwargs.update({'__impl':_select()})

        # self has application attribute, which is the definition of the Application
        super(SelectCycle, self).__init__(*args, **kwargs)


    def trigger_handlers(self,kw):
        '''
        this method for layout the handlers user define in the main.py.
        if user pass an object inherit Configs.Application, that means
        self has been set application parameter, which is the Application
        user defines, has many useful attribute for later calling.
        :param kw:  passed form the super class, has been wrapped
        :return: the handlers property. defined in main.py which is subclass
                of HttpRequest and added into the handlers key-value pair
        '''
        app = self.application()
        if app:
            return app.handlers
        return kw.get('handlers',[])


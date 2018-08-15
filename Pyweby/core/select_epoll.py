import select
from .Looper import PollCycle
from .config import Configs

class EpollCycle(PollCycle,Configs.BarrelCheck):
    '''
    The select model is limited by the number of file descriptors,
    so it is typically a maximum of 1024 sockets, and epoll breaks this limit.

    Epoll uses the event notification mechanism, instead of polling
    the status of each file descriptor one by one, saving CPU time.

    Epoll is the advanced version of select. In general, epoll is more efficient.
    '''
    _select = select.epoll()

    def __init__(self, *args,**kwargs):
        self.application = None
        flag, obj = self.if_define_barrel(args, kwargs)
        if flag and obj:
            self.wrapper_barrel(obj, kwargs)
        kwargs.update({'__impl': self._select})
        kwargs.update(self.application.settings)
        super(EpollCycle, self).__init__(*args, **kwargs)
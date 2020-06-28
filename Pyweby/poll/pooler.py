import select

import itertools
import socket
from poll.looper import PollCycle
from common.logger import Logger,traceback
from poll.check import BarrelCheck
from common.config import Configs

Log = Logger(logger_name=__name__)

class _select(object):
    def __init__(self):
        self.read_fds =  set()
        self.write_fds = set()
        self.error_fds = set()
        # self.fd_sets = (self.read_fds, self.write_fds, self.error_fds)

    def _debug(self):
        return [len(x) for x in (self.read_fds,self.write_fds,self.error_fds)]

    def sock_handlers(self,timeout):
        # Declare: this function is reference Tornado source code design.
        try:
        # Warning!
        # if you close an socket and not call remove_sock from the xxx_fds,
        # that's will cause mortal Error `ValueError: file descriptor cannot be a negative integer (-1)`
        # you can try `print(self.read_fds, self.write_fds, self.error_fds)`
        # to find the reason. (cause when sock close, sock.fd = -1)
            readable, writeable, exceptions = select.select(self.read_fds, self.write_fds, self.error_fds, timeout)
        except (ValueError,OSError,select.error,socket.error) as e:
            Log.critical(traceback(e))
            self.remove_negative_fd()
            return []
        events = {}
        for fd in readable:
            events[fd] = Configs.R
        for fd in writeable:
            events[fd] = Configs.W
        for fd in exceptions:
            events[fd] = Configs.E
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

    def remove_negative_fd(self):
        for i in itertools.chain(self.read_fds,self.write_fds,self.error_fds):
            if i.fileno() < 0:
                self.remove_sock(i)


class SelectCycle(PollCycle, BarrelCheck):
    def __init__(self,*args, **kwargs):
        flag, obj = self.if_define_barrel(args,kwargs)
        if flag and obj:
            self.wrapper_barrel(obj,kwargs)
            # after wrapper_barrel called, self is bind application instance
            # which is the class user defined inherit from Application
        self.check_application(kwargs)
        kwargs.update({'__impl':self.get_selector()()})
        # self has application attribute, which is the definition of the Application
        # now super calling .
        super(SelectCycle, self).__init__(*args, **kwargs)

    def get_selector(self):
        if hasattr(select, 'epoll'):
            return select.epoll
        elif hasattr(select, "kqueue"):
            return select.kqueue
        elif hasattr(select,'select'):
            return _select

# coding:utf-8


"""
For Mac OS X and BSD OS
"""

import select
from .Looper import PollCycle
from .config import Configs
from threading import Timer
from .Pooler import loading, SLASH
from cryptography.fernet import Fernet as Cipher


class KpollCycle(PollCycle, Configs.BarrelCheck):
    """
    The select model is limited by the number of file descriptors,
    so it is typically a maximum of 1024 sockets, and epoll breaks this limit.

    Epoll uses the event notification mechanism, instead of polling
    the status of each file descriptor one by one, saving CPU time.

    Epoll is the advanced version of select. In general, epoll is more efficient.
    """

    _KQUEUE = select.kqueue()

    def __init__(self, *args, **kwargs):
        Timer(0.1, loading(4))

        self.application = None
        flag, obj = self.if_define_barrel(args, kwargs)
        if flag and obj:
            self.wrapper_barrel(obj, kwargs)

        if self.application:

            kwargs.update(self.application.settings)
            safe_cookie = self.application.settings.get('safe_cookie')
            if not safe_cookie:
                raise ValueError('safe_cookie must be set in Application\'s setting')
            self.application.settings['safe_cookie_handler'] = Cipher(safe_cookie)


        kwargs.update({'__impl': self._KQUEUE})
        super(KpollCycle, self).__init__(*args, **kwargs)


    def trigger_handlers(self,kw):
        """
        this method for layout the handlers user define in the main.py.
        if user pass an object inherit Configs.Application, that means
        self has been set application parameter, which is the Application
        user defines, has many useful attribute for later calling.
        :param kw:  passed form the super class, has been wrapped
        :return: the handlers property. defined in main.py which is subclass
            of HttpRequest and added into the handlers key-value pair
        """

        app = self.application
        if app:
            handlers = []
            tmp = app.handlers
            for i, j in tmp:
                if i.startswith(SLASH):
                    pass
                else:
                    i = SLASH + i
                handlers.append((i, j))

            prefix = app.settings.get('uri_prefix',None)

            if prefix:
                if prefix.startswith('/'):
                    pass
                else:
                    prefix = '/' + prefix
                mapper = map(lambda i: (prefix + i[0], i[1]), handlers)
                if isinstance(mapper, map):
                    return list(mapper)
                return mapper
            return handlers
        return kw.get('handlers', [])
#coding: utf-8
import itertools
from .app import Application
from cryptography.fernet import Fernet as Cipher

class BarrelCheck(object):

    def __init__(self):
        self.application = None
        self.settings = None

    def if_define_barrel(self, args, kwargs):
        for i in itertools.chain(args, kwargs.keys()):
            if isinstance(i, self.__class__.__class__) and issubclass(i, Application):
                return True, i

        return False, None

    def wrapper_barrel(self, obj, kwargs):
        '''
        add application method, wrapper it to an instance attribute
        bind kwargs of SelectCycle.
        '''
        obj = obj()
        kwargs.update({'application': obj})
        self.application = obj

    def check_application(self, kwargs):
        if self.application:
            kwargs.update(self.application.settings)
            safe_cookie = self.application.settings.get('safe_cookie')
            if not safe_cookie:
                raise ValueError('safe_cookie must be set in Application\'s setting')
            self.application.settings['safe_cookie_handler'] = Cipher(safe_cookie)


class ChooseSelector(object):

    def __init__(self, flag=False):
        self.flag = flag

    def server_forever(self, debug=False):
        if self.flag == "EPOLL":
            self.server_forever_epoll(debug=debug)
        elif self.flag == "KQUEUE":
            self.server_forever_kqueue(debug=debug)
        else:
            self.server_forever_select(debug=debug)

    def server_forever_epoll(self, **kw):
        raise NotImplementedError

    def server_forever_select(self, **kw):
        raise NotImplementedError

    def server_forever_kqueue(self, **kwargs):
        raise NotImplementedError

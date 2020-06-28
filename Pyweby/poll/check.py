#coding: utf-8
import itertools
from .app import Application
from cryptography.fernet import Fernet as Cipher
from common.exception import NoRouterHandlers, FormatterError
from handle.request import HttpRequest

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

    @classmethod
    def check_handlers(cls, handlers):
        if len(handlers) <= 0:
            raise NoRouterHandlers
        for uri, obj in handlers:
            assert callable(obj)
            if isinstance(uri, (str, bytes)) and issubclass(obj, HttpRequest):
                continue
            else:
                raise FormatterError(uri=uri, obj=obj)

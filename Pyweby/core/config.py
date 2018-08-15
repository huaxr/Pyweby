#coding:utf-8
import types

import itertools


class Configs(object):
    R = 0x01
    W = 0x04
    E = 0x08
    M = 0x0F  #for main socket

    class Application(object):
        def __init__(self,handlers=None,settings=None):

            self.ok_value(self)
            assert isinstance(handlers, (list,tuple,set)) and len(handlers) > 0, 'NO Handlers'
            assert isinstance(settings,dict), 'Settings value must be a dict object'
            self.handlers = handlers
            self.settings = settings


        def get_handlers(self):
            return self.handlers

        def get_settings(self):
            return self.settings

        def ok_value(self,arg):
            if '__impl' in dir(arg):
                raise SyntaxError('keyword argument repeated of this application\'s self')


    class BarrelCheck(object):

        def __init__(self):
            self.application = None
            self.settings = None

        def if_define_barrel(self,args,kwargs):
            for i in itertools.chain(args, kwargs.keys()):
                if isinstance(i, self.__class__.__class__) and issubclass(i,Configs.Application):
                    return True,i

            return False,None

        def wrapper_barrel(self,obj, kwargs):
            '''
            add application method, wrapper it to an instance attribute
            bind kwargs of SelectCycle.
            '''
            kwargs.update({'application':obj()})
            self.application = obj()
            # self.settings = self.application.settings


    class ChooseSelector(object):

        def __init__(self, flag=False):
            self.flag = flag

        def server_forever(self, debug=False):
            if self.flag:
                self.server_forever_epoll(debug=debug)
            else:
                self.server_forever_select(debug=debug)

        def server_forever_epoll(self, **kw):
            raise NotImplementedError

        def server_forever_select(self, **kw):
            raise NotImplementedError



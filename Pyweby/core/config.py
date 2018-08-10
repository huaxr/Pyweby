#coding:utf-8

class Configs(object):
    R = 0x01
    W = 0x04
    E = 0x08
    M = 0x0F  #for main socket

    def __new__(cls,*args,**kwargs):
        _impl = cls.config_impl()
        instance = super(Configs, cls).__new__(_impl)
        print instance
        return instance

    @classmethod
    def config_impl(cls):
        return cls.config_define()

    @classmethod
    def config_define(cls):
        raise NotImplementedError


class SocketPool(Configs):
    def __init__(self):
        pass

    def config_define(self):
        return SockCycle




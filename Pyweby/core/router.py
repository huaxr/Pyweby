import select
from poll.pooler import SelectCycle

try:
    from poll.epoller import EpollCycle
except (ImportError, AttributeError):
    EpollCycle = SelectCycle

try:
    from poll.kpoller import KpollCycle
except (ImportError, AttributeError):
    KpollCycle = SelectCycle


class Router(object):

    def __new__(cls, *args, **kwargs):

        impl = cls.configure()
        # impl__call__() is impl(), which is KpollCycle object
        try:
            instance = super(Router, cls).__new__(impl.__call__())
        except TypeError as e:
            raise e

        cls.ok_value(instance)

        return instance.__class__

    def __init__(self,*args,**kwargs):

        super(self.__class__,self).__init__()

    @classmethod
    def ok_value(cls, instance):
        assert isinstance(instance, (SelectCycle, EpollCycle, KpollCycle,)), 'Error base instance to handler'


    @classmethod
    def configure(cls):
        '''
        for safe reason, do not call impl immediate
        :return: bound method _choose of class `router.Looper`
        '''
        base = cls._choose()
        return base

    @classmethod
    def _choosen(cls):
        raise NotImplementedError

    @classmethod
    def _choose(cls):
        raise NotImplementedError

    def get_sock(self):
        raise NotImplementedError

    @staticmethod
    def checing_return(*args,**kwargs):

        def wrapper(fn):

            return fn(*args,**kwargs)

        return wrapper


class DistributeRouter(Router):
    connection = None

    @classmethod
    def get_sock(cls):
        return cls.connection

    @classmethod
    def set_sock(cls,conn):
        cls.connection = conn
        return cls

    @classmethod
    def _choosen(cls):
        if hasattr(select, 'epoll'):
            from core.Epoller import EpollCycle
            return EpollCycle
        if hasattr(select, "kqueue"):
            # on BSD or Mac OS X
            return KpollCycle

        if hasattr(select,'select'):
            return SelectCycle

        else:
            raise NotImplementedError


    @classmethod
    def _choose(cls):
        return cls._choosen

    def find_router(self):
        raise NotImplementedError


class Looper(DistributeRouter):
    def __init__(self, handlers=None, enable_manager=False, *args, **kwargs):
        self.handlers = handlers
        self.enable_manager = enable_manager
        self.template_path = kwargs.get('template_path', '')
        self.static_path = kwargs.get('static_path', '')
        super(Looper, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def listen(self,port):
        '''
        listen on port sock is main server Select IO Loop
        :param port: int value
        :return:
        '''
        raise NotImplementedError

    def server_forever(self):
        '''
        starting the server to `sniffer` all http request
        and wrapper to request and response object
        :return:
        '''
        raise NotImplementedError



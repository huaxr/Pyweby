import select
from core.select_select import SelectCycle

class Router(object):

    def __new__(cls, *args, **kwargs):

        impl = cls.configure()
        '''
        To figure out that the impl is callable object
        '''
        try:
            instance = super(Router, cls).__new__(impl.__call__())
        except TypeError as e:
            raise e

        cls.ok_value(instance)

        return instance.__class__

    def __init__(self,*args,**kwargs):

        super(self.__class__,self).__init__()

    @classmethod
    def ok_value(cls,ins):
        raise NotImplementedError


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
            raise NotImplementedError
        if hasattr(select,'select'):
            return SelectCycle

    @classmethod
    def _choose(cls):
        return cls._choosen

    def get(self):
        pass

    def post(self):
        pass

    def put(self):
        pass

    def options(self):
        pass

    def delete(self):
        pass

    def find_router(self):
        raise NotImplementedError

    @classmethod
    def ok_value(cls,instance):
        assert isinstance(instance, (SelectCycle,)), 'Error base instance to handler'


class Looper(DistributeRouter):

    def __init__(self,*args,**kwargs):

        super(Looper,self).__init__(*args,**kwargs)

    def __call__(self, *args, **kwargs):
        return self.listen(kwargs.get('port',8000))

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


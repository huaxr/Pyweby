class Router(object):
    def __new__(cls, *args, **kwargs):
        impl = cls.configured_class()
        instance = super(Router, cls).__new__(impl)
        return instance

    @classmethod
    def configured_class(cls):
        base = cls.configurable_base()
        base.__impl_class = cls.configurable_default()
        return base.__impl_class

    @classmethod
    def configurable_base(cls):
        raise NotImplementedError

    @classmethod
    def configurable_default(cls):
        raise NotImplementedError

    def get_sock(self):
        raise NotImplementedError


class DistributeRouter(object):
    connection = None

    @classmethod
    def get_sock(cls):
        return cls.connection

    @classmethod
    def set_sock(cls,conn):
        cls.connection = conn
        return cls

    @classmethod
    def configurable_base(cls):
        return DistributeRouter

    @classmethod
    def configurable_default(cls):
        return cls.connection

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
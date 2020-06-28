#coding: utf-8
from common.exception import MethodNotAllowedException, JsonPraseError
from common.config import Configs
from common.compat import _None
import json
from common.exception import InspectorError
from common.compat import STRING

def set_header_check(fn):
    def wrapper(*args):
        if not (len(args)==3 and any(isinstance(i,STRING) for i in [args[1:]])):
            raise InspectorError(msg="Arguments check error.", type='arguments')
        return fn(*args)
    return wrapper

def set_headers_check(fn):
    def wrapper(*args):
        if len(args)==2 and isinstance(args[1], dict):
            return fn(*args)
        else:
            raise InspectorError(type='arguments')
    return wrapper

def thread_state(fn):
    def wrapper(self):
        if not (hasattr(self, 'eventManager') and hasattr(self, 'peventManager')):
            raise RuntimeError("Thread not started yet.")
        return fn

    return wrapper


class method_check(object):
    def __init__(self,fn):

        self.func = fn

    def __contains__(self, item):
        return item in Configs.METHODS

    def __get__(self,instance,cls=None):

        if instance is None:
            return self
        res = self.func(instance)

        if len(res) > 2 and res[0] in self:
            return res
        else:
            raise MethodNotAllowedException(method=res[1])


def except_handler(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            return None
    return wrapper



class _property(property):
    '''
    wrapped magic.

    '''
    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

        super(_property,self).__init__()

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, instance, owner=None):

        '''
        keeping the result in the obj.__dict__.
        __dict__ is instance's bindings. so, this make keeping result
        and don't need call method twice.

        >>> class Test(object):
        >>>    @_property
        >>>    def func(self):
        >>>       self.name = 111
        >>>        a = 1
        >>>        b = 2
        >>>        return a+b

        >>> a = Test()
        >>> c = a.func
        >>> print(a.__dict__)
        :return: {'func': 3}
        '''
        if instance is None:
            return self
        value = instance.__dict__.get(self.__name__, _None)
        if value is _None:
            value = self.func(instance)
            instance.__dict__[self.__name__] = value
        return value

class restful(object):
    def __init__(self,fn):
        self.fn = fn

    def __get__(self, instance, cls=None):

        if instance is None:
            return self
        result = self.fn(instance)
        # assert isinstance(result,(list,tuple)) and len(result) == 2
        tmp = {}
        if isinstance(result, (list, tuple)) and len(result) == 2:
            tmp['res'] = result[0]
            tmp['status'] = result[1]
        else:
            tmp['res'] = result
            tmp['status'] = 200
        try:
            json.dumps(tmp)
        except Exception:
            raise JsonPraseError('Error format')
        return tmp
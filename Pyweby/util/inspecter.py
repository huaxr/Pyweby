from handle.exc import InspectorError
from ._compat import STRING

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

def observer_check(fn):
    def wrapper(*args):
        if len(args)==2 and hasattr(args[1], '_make'):
            return fn(*args)
        else:
            raise InspectorError(msg='args needs an namedtuple like object.',type='arguments')
    return wrapper

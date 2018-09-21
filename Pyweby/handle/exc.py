import sys
from collections import namedtuple

_exceptions = {}



class MethodNotAllowedException(Exception):
    def __init__(self,msg=None,method=None):
        super(MethodNotAllowedException,self).__init__(msg or '{} method is not allowed!'.format(method))


class NoRouterHandlers(Exception):
    def __init__(self,msg=None):
        super(NoRouterHandlers,self).__init__(msg or 'No handler to deal with request')


class FormatterError(Exception):
    def __init__(self,msg=None,uri=None,obj=None):
        super(FormatterError,self).__init__(msg
                                            or 'handlers formatter error,({uri},{obj})'.format(uri=uri,obj=obj))

class StatusError(Exception):
    def __init__(self,msg=None,status=None):
        super(StatusError,self).__init__(msg or 'status {} is not allowed, must be int and 200=<x<=500'.format(status))


class NoPackageFound(Exception):
    def __init__(self, msg=None, pkname=None):
        super(NoPackageFound, self).__init__(msg or 'package {} is not found, try `pip install {}` '.format(pkname,pkname))


class EventManagerError(Exception):
    def __init__(self, msg=None):
        super(EventManagerError, self).__init__(msg or 'For Future result. you must set enable_manager=True!')

class NoHandlingError(Exception):
    def __init__(self, msg=None):
        super(NoHandlingError, self).__init__(msg or 'There is no handing for the specific branch yet')

class JsonPraseError(Exception):
    def __init__(self, msg=None):
        super(JsonPraseError, self).__init__(msg or 'JsonPraseError, You may passed an callable object that json could not prase it')

class ProtocolError(Exception):
    def __init__(self, msg=None):
        super(ProtocolError, self).__init__(msg or 'The HTTP Request Protocol Error')


class ApplicationError(Exception):
    def __init__(self, msg=None):
        super(ApplicationError, self).__init__(msg or 'Application Error')

class JSONFormatError(Exception):
    def __init__(self, msg=None):
        super(JSONFormatError, self).__init__(msg or 'JSON ERROR')

class ExceptHandler(Exception):
    def __init__(self,func):
        self.func = func

    def __get__(self, instance, owner):
        try:
            return self.func(instance)
        except Exception as e:
            return e


class _HttpException(Exception):
    def __init__(self,status,msg=None):
        if msg:
            super(_HttpException,self).__init__(status,msg)
        else:
            super(_HttpException, self).__init__(status)


@eval('lambda x:x')
class HTTPExceptions(Exception):
    def __init__(self,response=None,message=None):
        self.message = None
        super(HTTPExceptions,self).__init__()
        if message is not None:
            self.message = message

        self.response = response

    @classmethod
    def wrap(cls,exception,name=None):
        class newcls(cls,exception):
            def __init__(self,arg=None,*args,**kwargs):
                cls.__init__(self,*args,**kwargs)
                exception.__init__(self,arg)
        newcls.__module__ = sys._getframe(1).f_globals.get('__name__')
        newcls.__name__ = name or cls.__name__ + exception.__name__

        return newcls


    def raiser(self,*args, **kwargs):

        raise _HttpException(self.response,self.message) or BaseException(self.response,self.message)


    __call__ = raiser


class Abort(object):
    def __init__(self,mapping=None, extra=None):
        if mapping is None:
            mapping = _exceptions
        self.mapping = dict(mapping)
        if extra is not None:
            self.mapping.update(extra)

    def __call__(self,code, *args, **kwargs):
        if not args and isinstance(code, int):
            raise HTTPExceptions(response=code)()

        if args and isinstance(code, int):

            raise HTTPExceptions(response=code,message=args[0])()

        if code not in self.mapping:
            raise LookupError('no exception for %r' % code)

        raise self.mapping.get(code,400)(*args,**kwargs)


class ORMError(Exception):
    def __init__(self,msg=None):
        super(ORMError,self).__init__(msg or self.__class__.__name__)



class InspectorError(Exception):
    def __init__(self, msg=None,type=None):
        if type == 'arguments':
            super(InspectorError, self).__init__(msg or 'InspectorError when parse {}'.format(type.title()))

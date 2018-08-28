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


class ExceptHandler(Exception):
    def __init__(self,func):
        self.func = func

    def __get__(self, instance, owner):
        try:
            return self.func(instance)
        except Exception as e:
            return e

from poll.pooler import SelectCycle

class Router(object):

    def __new__(cls, *args, **kwargs):
        try:
            instance = super(Router, cls).__new__(SelectCycle)
        except TypeError as e:
            raise e

        cls.ok_value(instance)

        return instance.__class__

    def __init__(self,*args,**kwargs):

        super(self.__class__,self).__init__()

    @classmethod
    def ok_value(cls, instance):
        assert isinstance(instance, SelectCycle), 'Error base instance to handler'


class Looper(Router):
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



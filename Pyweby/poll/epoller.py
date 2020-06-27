import select
from .looper import PollCycle
from threading import Timer
from .pooler import loading,SLASH
from cryptography.fernet import Fernet as Cipher
from .check import BarrelCheck

class EpollCycle(PollCycle, BarrelCheck):
    _select = select.epoll()

    def __init__(self, *args,**kwargs):
        Timer(0.1, loading(4))

        self.application = None
        flag, obj = self.if_define_barrel(args, kwargs)
        if flag and obj:
            self.wrapper_barrel(obj, kwargs)
        self.check_application(kwargs)
        kwargs.update({'__impl': self._select})
        super(EpollCycle, self).__init__(*args, **kwargs)


    def trigger_handlers(self,kw):
        app = self.application
        if app:
            handlers = []
            tmp = app.handlers
            for i, j in tmp:
                if i.startswith(SLASH):
                    pass
                else:
                    i = SLASH + i
                handlers.append((i, j))

            prefix = app.settings.get('uri_prefix',None)

            if prefix:
                if prefix.startswith('/'):
                    pass
                else:
                    prefix = '/' + prefix
                mapper = map(lambda i: (prefix + i[0], i[1]), handlers)
                if isinstance(mapper, map):
                    return list(mapper)
                return mapper
            return handlers
        return kw.get('handlers',[])
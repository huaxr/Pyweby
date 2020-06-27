#coding: utf-8
from config.config import Global

class Application(object):
    def __init__(self, handlers=None, settings=None):
        self.ok_value(self)
        assert isinstance(handlers, (list, tuple, set)) and len(handlers) > 0, 'NO Handlers'
        assert isinstance(settings, dict), 'Settings value must be a dict object'
        self.handlers = handlers
        self.settings = settings
        self._init()

    def _init(self):
        global Global
        Global += self.settings

    def get_handlers(self):
        return self.handlers

    def get_settings(self):
        return self.settings

    def ok_value(self, arg):
        if '__impl' in dir(arg):
            raise SyntaxError('keyword argument repeated of this application\'s self')
import ssl
import time
import os

from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs
from core.concurrent import Executor,asyncpool
from handle.response import restful,cache_result

class testRouter(HttpRequest):
    def get(self):
        # test for redirect
        return self.request.redirect("/hello?key=2")

    def post(self):
        # ignore_cache is a cache enable flag
        return self.request.render("index.html",tmp=[1,2,3],ignore_cache=False)


class testRouter2(HttpRequest):
    executor = Executor((os.cpu_count() or 1) * 5)

    @asyncpool(executor=executor)
    def sleeper(self,counts):
        time.sleep(counts)
        return "sleeper call over, %d" %(counts)

    def get(self):
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)
        return result, 200

    @restful  # test from restful api
    def post(self):
        # test for async concurrent and non-blocking Future
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        return {'test':'test','test2':[1,2,3,4],'test3':{'xx':value}},200


class testRouter3(HttpRequest):
    @restful           # use restful before the cache_result !
    @cache_result(expiration=60)
    def get(self):
        time.sleep(5)
        return "Hello World",200


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/hello',testRouter2),
                         (r'/', testRouter),
                         (r'/test', testRouter3),]
        self.settings = {
            "enable_manager":True,   # if you want get the Future.result and without blocking the server. set it True
            "ssl_options": {"ssl_enable": 1,
                            "ssl_version": ssl.PROTOCOL_SSLv23,
                            "certfile": os.path.join(os.path.dirname(__file__), "static","server.crt"),
                            "keyfile": os.path.join(os.path.dirname(__file__), "static","server.key")},

            "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
            "static_path" : os.path.join(os.path.dirname(__file__), "static"),
        }
        self.test = "test message"
        super(Barrel,self).__init__(self.handlers,self.settings)

    def global_test(self):
        print('global test')


if __name__ == '__main__':
    loop = Looper()
    server = loop(Barrel) or loop(handlers=[(r'/hello',testRouter2),],enable_manager=1)
    server.listen()
    server.server_forever(debug=False)



import ssl
import time
import os
from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs
from core._concurrent import Executor,asyncpool
from handle.response import restful,cache_result
from handle.auth import login_require
from util._compat import COUNT

class testRouter(HttpRequest):
    def post(self):
        # test for redirect
        return self.request.redirect("/2?key=2")

    def get(self):
        # ignore_cache is a cache enable flag
        return self.request.render("upload.html",name=[1,2,3],ignore_cache=False)


class testRouter2(HttpRequest):
    executor = Executor(COUNT)

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
        return self.request.form.lname   # form support
        # return self.request.get_arguments('lname','xxxx')

class testRouter3(HttpRequest):
    @restful           # use restful before the cache_result !
    @cache_result(expiration=60)
    def post(self):
        time.sleep(5)
        return "Hello World",200

    @restful
    def get(self):
        name = self.request.get_arguments('name', 'defalut')
        self.request.set_cookie({'name':name,'pass':name,'xxx':'xxx','login':True}, expires=66,safe_type="encrypt")
        yy = self.request.get_cookie(safe_type="encrypt")

        self.request.set_cookie({'name': name, 'pass': name, 'xxx': 'xxx', 'login': True}, expires=66,
                                safe_type="db_session")
        xx = self.request.get_cookie(safe_type="db_session")

        self.request.clear_cookie()
        return xx


# @login_require
class testRouter4(HttpRequest):
    def get(self):
        self.request.get_xml()
        self.request.get_json()

    def post(self):
        print(self.request.file)

class testRouter5(HttpRequest):
    def get(self):
        return "xxxx"

class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/2',testRouter2),
                         (r'/1', testRouter),
                         (r'/3', testRouter3),
                         (r'/4', testRouter4),
                         (r'/5', testRouter5),]
        self.settings = {
            "enable_manager":True,   # if you want get the Future.result and without blocking the server. set it True
            "ssl_options": {"ssl_enable": 1,
                            #TODO SSL with python2.7 env will reach ssl.Error PEM lib (_ssl.c:2693)
                            "ssl_version": ssl.PROTOCOL_SSLv23,
                            "certfile": os.path.join(os.path.dirname(__file__), "static","server.crt"),
                            "keyfile": os.path.join(os.path.dirname(__file__), "static","server.key")},

            "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
            "static_path" : os.path.join(os.path.dirname(__file__), "static"),
            "safe_cookie" : 'YnicJQBLgFAbAaP_nUJTHMA3Eq-G9WpNeREQL-qljLE=',
            "database" : "mysql://127.0.0.1:3306/test",
        }
        self.test = "test message"
        super(Barrel,self).__init__(self.handlers,self.settings)

    def global_test(self):
        print('global test')


if __name__ == '__main__':
    loop = Looper()
    server = loop(Barrel) or loop(handlers=[(r'/hello',testRouter2),],enable_manager=1)
    server.listen(8888)
    server.server_forever(debug=False)



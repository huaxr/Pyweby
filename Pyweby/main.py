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
from util.ormEngine import User

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

class cookie(HttpRequest):
    @restful           # use restful before the cache_result !
    @cache_result(expiration=60)
    def post(self):
        time.sleep(5)
        return "Hello World",200

    def get(self):
        yy = self.request.get_cookie()
        return yy


@login_require
class admin(HttpRequest):
    def get(self):
        # cookies = self.request.get_cookie()
        # name = cookies['name']
        # priv = cookies['level']
        user = self.request.current_user()
        return "admin user %s, your priv is %s" %(user.name,user.can_upload)

    def post(self):
        user = self.request.current_user()
        if user.is_admin:
            filename = self.request.file.filename
            self.request.file.saveto("C:\\"+filename)
            return "success"
        else:
            return "sorry , only is_admin can upload files"


class register(HttpRequest):
    def get(self):
        name = self.request.get_arguments('name', '')
        passwd = self.request.get_arguments('passwd', '')
        level = self.request.get_arguments('level', 'R')
        with User(id='',user=name,passwd=passwd,privilege=level,information={'sign':'never give up','nickname':'华'}) as u:
            u.save()
        return "register ok. please login."



class logout(HttpRequest):
    def get(self):
        self.request.clear_cookie()
        return "clean ok"


class login(HttpRequest):
    def get(self):
        name = self.request.get_arguments('name', '')
        passwd = self.request.get_arguments('passwd', '')
        user =  User.get(user=name,passwd=passwd)

        if user and self.can_read(user):
            self.request.set_cookie({'name':name,'level':self.user_priv_dict(user)})
            return "%s login ok" %name + self.user_priv_dict(user)
        # user.is_admin()


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/2',testRouter2),
                         (r'/1', testRouter),
                         (r'/cookie', cookie),
                         (r'/admin', admin),
                         (r'/register', register),
                         (r'/logout', logout),
                         (r'/login', login),]

        self.settings = {
            "ssl_options": {"ssl_enable": 1,
                            #TODO SSL with python2.7 env will reach ssl.Error PEM lib (_ssl.c:2693)
                            "ssl_version": ssl.PROTOCOL_SSLv23,
                            "certfile": os.path.join(os.path.dirname(__file__), "static","server.crt"),
                            "keyfile": os.path.join(os.path.dirname(__file__), "static","server.key")},

            "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
            "static_path" : os.path.join(os.path.dirname(__file__), "static"),
            "safe_cookie" : 'YnicJQBLgFAbAaP_nUJTHMA3Eq-G9WpNeREQL-qljLE=',
            "DATABASE" : "mysql://127.0.0.1:3306/test/user=root&passwd=root", # "mongodb://127.0.0.1:27017/test"
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



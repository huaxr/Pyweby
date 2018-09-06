# Pyweby
Very Sexy Web Framework. Savvy?


### Futures
1. it's reliable ,compatible and convenient to using the project to start an web application.
1. concurrent future.result() is non-blocking by observer.
1. redirect 302 now support (using self.request.redirect)
1. restful api is easily back up(set descriptor @restful on the get or post method)
1. template rendering html is under ready (support major jinja2 render functionality, the same semanteme like Flask does!)
1. support SSL communication.
1. cookies and Authentication(@login_require) 
1. normal form handled. (TODO others Content-Type)
1. session with ORM. Provides another secure cookie session mechanism.
1. file uploading. big MB file will blocking main thread.
1. raise_status(400) like abort(400) does. will throw an Exception to client.
1. wrapperd all interface(9.3) in self(HttpRequest),e.g. you can use self.request.file, self.file as you want. they are the same.
1. More flexible and smooth ORM.
1. Addressing method supporting regular URI .e.g.（ (r'/string/([0-9]+)/sss/([0-5])/', testRouter),）
1. others: log system. cache system , malicious request analysis and disinfect and so on..
1. enhancing capacity is still a mystery, pay close attention to it [https://github.com/huaxr/Pyweby/]()

(支持所有web应用基本功能，包括常用api, 文件上传, json, xml 交互, 支持 epoll ,SSL ，并发,  多线程,  版本兼容, nginx 代理，用户权限cookie及session认证，微型ORM框架，模版渲染框架，丰富的自定义接口等)
- Currently env: python2.7 - python3.7 win or linux.


### MAIN CODE
##### easy example code to show it's power! 

**main.py**
```python
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
        # ignore_cache is a cache enable flag
        return self.render("upload.html",name=[1,2,3],ignore_cache=False)

    def get(self):
        # return self.redirect("/2?key=2")
        # self.raise_status(401,"sorry, you are not allowd")
        # return self.render("upload.html", name=[1, 2, 3], ignore_cache=False)
        c = User.get(user='hua').exclude(passwd='123').commit()
        for i in c:
            print(i)

class testRouter2(HttpRequest):
    executor = Executor(COUNT)

    @asyncpool(executor=executor)
    def sleeper(self,counts):
        time.sleep(counts)
        return "sleeper call over, %d" %(counts)

    def get(self):
        arguments = self.get_arguments('key', 'defalut')
        try:
            value = int(arguments)
        except Exception:
            value = 1
        result = self.sleeper(value)
        return result, 200

    @restful  # test from restful api
    def post(self):
        return self.form.lname   # form support

class cookie(HttpRequest):
    @restful           # use restful before the cache_result !
    @cache_result(expiration=60)
    def post(self):
        time.sleep(5)
        return "Hello World",200

    def get(self):
        yy = self.get_cookie()
        return yy


@login_require
class admin(HttpRequest):
    def get(self):
        user =  self.current_user or self.request.current_user()
        if user:
            return "admin user %s, your priv is %s" %(user.name,user.can_upload)
        else:
            self.set_header("xxxxx","yyy")
            self.raise_status(401)

    def post(self):
        user = self.current_user
        if user.can_upload:
            filename = self.file.filename
            print(filename)
            self.file.saveto("C:\\"+filename)
            return "success"
        else:
            return "sorry , only is_admin can upload files"


class register(HttpRequest):
    def get(self):
        name = self.get_arguments('name', '')
        passwd = self.get_arguments('passwd', '')
        level = self.get_arguments('level', 'R').upper()
        with User(id='',user=name,passwd=passwd,privilege=level,information={'sign':'never give up','nickname':'华'}) as u:
            u.save()
        return "register ok. please login."


class logout(HttpRequest):
    def get(self):
        self.clear_cookie()
        return "clean ok"


class login(HttpRequest):
    def get(self):
        name = self.get_arguments('name', '')
        passwd = self.get_arguments('passwd', '')
        user =  User.get(user=name,passwd=passwd)

        if user and self.can_read(user):
            self.set_cookie({'name':name,'level':self.user_priv_dict(user)})
            return "%s login ok" %name + self.user_priv_dict(user)
        # user.is_admin()


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/2/',testRouter2),
                         (r'/string/([0-9]+)/sss/([0-5])/', testRouter),
                         (r'/cookie/', cookie),
                         (r'/admin/', admin),
                         (r'/register/', register),
                         (r'/logout/', logout),
                         (r'/login/', login),]

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




```

### HttpRequest
- each interface that provides a web service must inherit from this class, implement its `get`, and `post` methods correspond to the `get` and `post` requests, respectively. 
```python
class testRouter(HttpRequest):
    def get(self):
        # test for redirect
        return self.request.redirect("/hello?key=2")

    def post(self):
        # ignore_cache is a cache enable flag
        return self.request.render("index.html",tmp=[1,2,3],ignore_cache=False)
```


### Barrel(Configs.Application)
- this is the Application settings. you can define global functions or set gloabl settings here.



### concurrent
- we kown concurrent.future() is a block state. using this will realizing real asynchronous.
```python
class testRouter2(HttpRequest):
    executor = Executor((os.cpu_count() or 1) * 5)
    @asyncpool(executor=executor)
    def sleeper(self,counts):
        time.sleep(counts)
        return "sleeper call over, %d" %(counts)
    @restful  # test from restful api
    def get(self):
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)
        return result, 200
```



### redirect (301 or 302 status)
- this will tell the client to referring the uri server provides.
```python
def get(self):
    return self.request.redirect("/hello?key=2")
```


### Template(render html)
- rendering Engine is internally installed. just like almost rendering Engine dose, it's lightly implement.
```python
def get(self):
    # ignore_cache is a cache enable flag
    return self.request.render("index.html",tmp=[1,2,3],ignore_cache=False)
```


### SSL
- add the `ssl_options` in the Barrel.settings, you can easily swich the ssl_enable flag to  deploy the web listing 443 or 80 port, use https to access the handler.
```python
"ssl_options": {"ssl_enable": True,  # support ssl for secure reason
                "ssl_version": ssl.PROTOCOL_SSLv23,
                "certfile": os.path.join(os.path.dirname(__file__), "static","server.crt"),
                "keyfile": os.path.join(os.path.dirname(__file__), "static","server.key")},
```

### Restful
- using @restful decorator will return the web page with Content-Type: application/json header.
```python
@restful  # test from restful api
def get(self):
    arguments = self.request.get_arguments('key', 'defalut')
    value = int(arguments)
    return {'test':'test','test2':[1,2,3,4],'test3':{'xx':value}},200
```

### Cache
- using @cache_restful decorator will cache the return result in the cache Engine.
- if you want cache an restful result. please add @restful before the @cache_result.
(prameter expiration must set int, this means 60 second later , cache will disable. )
```python
class testRouter3(HttpRequest):
    @restful          
    @cache_result(expiration=60)
    def get(self):
        time.sleep(5)
        return "Hello World",200
```

### Form
```python
def get(self):
    # ignore_cache is a cache enable flag
    return self.request.render("form.html",name=[1,2,3],ignore_cache=False)
    
 # render a form html and post to /2
 # <p>Last name: <input type="text" name="lname" /></p>

@restful  # test from restful api
def post(self):
    return self.request.form.lname  
```

### Cookies
- if you wanna use cookie. please set safe_cookie in the app's settings like this:
"safe_cookie" : 'YnicJQBLgFAbAaP_nUJTHMA3Eq-G9WpNeREQL-qljLE='
- use set_cookie and get_cookie from the self.request instance to access the headers.
- safe options will use crypto to make it security.
 - `set_cookie` Set the encrypted cookies dict .
 - `get_cookie` Get the decrypted cookie
 - `clear_cookie` for logout.

```python
    def get(self):
        # name = self.request.get_arguments('name', 'defalut')
        # self.request.set_cookie({'name':name,'pass':name,'xxx':'xxx'}, expires=66,safe=True)
        xx = self.request.get_cookie()
        # self.request.clear_cookie() logout
        return xx,200
```

### Authentication
- use this decorator @login_require to declare this RequestHandler's get and post method is need authentication.
- it also means that specific URI will accept authentication conditions.
- login_require will check the cookie if a legitimate one and response 401 or 200 status to browser.

```python
@login_require
class admin(HttpRequest):
    def get(self):
        user =  self.current_user or self.request.current_user()
        if user:
            return "admin user %s, your priv is %s" %(user.name,user.can_upload)
        else:
            self.set_header("xxxxx","yyy")
            self.raise_status(401)

    def post(self):
        user = self.current_user
        if user.can_upload:
            filename = self.file.filename
            print(filename)
            self.file.saveto("/tmp"+filename)
            return "success"
        else:
            return "sorry , only is_admin can upload files"
```

### ORM session. 8.25
- set_cookies and get_cookies support two secuty ways:
- safe_type = "encrypt" will using third party encryption library to encrypt cookie。
- safe_type = "db_session" will using orm (mysql support now) Session keeping the session in database.
```python
@restful
def get(self):
    name = self.request.get_arguments('name', 'defalut')
    self.request.set_cookie({'name':name,'pass':name,'xxx':'xxx','login':True}, expires=66,safe_type="encrypt")
    yy = self.request.get_cookie(safe_type="encrypt")

    self.request.set_cookie({'name': name, 'pass': name, 'xxx': 'xxx', 'login': True}, expires=66,
                            safe_type="db_session")
    xx = self.request.get_cookie(safe_type="db_session")
    return xx
```
- the db_session looks like this:

![mark](http://pacfhd1z8.bkt.clouddn.com/python/180825/kbekDgDB2C.png?imageslim)


### File uploading
you can use self.request.file acquire file information. such as filename, file raw data.
call saveto to save file in the path.
```python
class testRouter4(HttpRequest):
    def get(self):
        self.request.get_xml()
        self.request.get_json()

    def post(self):
        filename = self.request.file.filename
        self.request.file.saveto("C:\\"+filename)
        return "success"
```

### raise_status
- when you raise the function and give an status(int) or msg(str). return the exception you set:e.g.
```python
def get(self):
    self.raise_status(401,"sorry, you are not allowd")
```
![mark](http://pacfhd1z8.bkt.clouddn.com/python/180903/gBf0HaKFF4.png?imageslim)


### flexible and smooth ORM
- using this like below will search User Table like sql: 
'select * from User where user=hua and passwd!=123'
```python
def get(self):
    c = User.get(user='hua').exclude(passwd='123').commit()
    assert isinstance(c,types.GenType)
```

### regex uri
- if you referer "https://10.74.154.45:8888/string/123/sss/2/" , than you can use self.matcher get the result:
[('123','2')]


### log
- every request will gererate a log. just like this:
```
[16:53:52] [*] Hello, administrator@Pyweby master.
[16:53:53] [*] Server https://10.74.154.45:8888 started! fd=[404]
[16:53:53] Method			From			Index
[16:53:58] GET		10.74.154.45		/string/123/sss/2/
```


### USAGE

```
>> curl https://127.0.0.1:8000/hello?key=5

at the same time , starting another console and input:

>> curl -XPOST https://127.0.0.1:5000/hello -d "key=5"

which means start 2 request , every request will block key=5 seconds,
but infusive thing is that both are returned at the same time.


Notice:
1. when using redirect , do not use curl for a test.

hope for enjoy!

```

### 并发测试

并发数:10000

![mark](http://pacfhd1z8.bkt.clouddn.com/python/180814/gcGe28dIm5.png?imageslim)


later useage is Unfinished.

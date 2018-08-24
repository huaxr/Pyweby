# Pyweby
An awesome non-blocking web server achieved by python3, create for surpassing Tornado and Django!


### Futures
1. it's reliable ,compatible and convenient to using the project to start an web application.
1. concurrent future.result() is non-blocking by observer.
1. redirect 302 now support (using self.request.redirect)
1. restful api is easily back up(set descriptor @restful on the get or post method)
1. template rendering html is under ready (support major jinja2 render functionality, the same semanteme like Flask does!)
1. support SSL communication.
1. cookies and Authentication(@login_require) 
1. others: log system. cache system , malicious request analysis and disinfect and so on..
1. enhancing capacity is still a mystery, pay close attention to it [https://github.com/huaxr/Pyweby/]()

- Currently in window+python3.6 environment test development


### MAIN CODE
##### easy example code to show it's power! 

**main.py**
```python
import ssl

from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs

from core.concurrent import Executor,asyncpool
from handle.response import restful
import time
import os

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

    @restful  # test from restful api
    def get(self):
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        return {'test':'test','test2':[1,2,3,4],'test3':{'xx':value}},200

    def post(self):
        # test for async concurrent and non-blocking Future
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)
        return result, 200


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
            "ssl_options": {"ssl_enable": True,  # support ssl for secure reason
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

### Cookies
- if you wanna use cookie. please set safe_cookie in the app's settings like this:
"safe_cookie" : 'YnicJQBLgFAbAaP_nUJTHMA3Eq-G9WpNeREQL-qljLE='
- use set_cookie and get_cookie from the self.request instance to access the headers.
- safe options will use crypto to make it security.
```python
    def get(self):
        # name = self.request.get_arguments('name', 'defalut')
        # self.request.set_cookie({'name':name,'pass':name,'xxx':'xxx'}, expires=66,safe=True)
        xx = self.request.get_cookie()
        print("xxx",xx)
        return 'xx',200
```

### Authentication
- use this decorator @login_require to declare this RequestHandler's get and post method is need authentication.
- it also means that specific URI will accept authentication conditions.
- login_require will check the cookie if a legitimate one and response 401 or 200 status to browser.

```python
@login_require
class testRouter4(HttpRequest):
    def get(self):
        name = self.request.get_arguments('name', 'defalut')
        return name,200
```


### log
- every request will gererate a log. just like this:
```
[18:57:14] Server https://10.74.154.57:443 started! fd=[368]
[18:57:20] GET		10.74.154.57		/
[18:57:20] GET		10.74.154.57		/hello?key=2
[18:57:38] GET		10.74.154.57		/test?name=pyweby
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

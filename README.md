# Pyweby
An awesome non-blocking web server achieved by python3, create for surpassing Tornado and Django!


### Futures
1. it's convenient and reliable to using the project to start an web application.
1. concurrent Future.result() is non-blocking by Observer.(it's really great future)
1. compatible with python3 and python2 ,win , linux.
1. redirect 302 now support (using self.request.redirect)-- 2018.8.15
1. restful api (set descriptor @restful on the get or post method)
1. enhancing capacity is still a mystery, pay close attention to it [https://github.com/huaxr/Pyweby/]()


### MAIN CODE
##### easy example code to show it power! 

**main.py**
```
from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs

from core.concurrent import Executor,asyncpool
import time
import os

class testRouter(HttpRequest):
    '''
    Test for redirect !
    '''
    def get(self):
        self.request.redirect("/hello?key=2")

class testRouter2(HttpRequest):
    executor = Executor((os.cpu_count() or 1) * 5)

    @asyncpool(executor=executor)
    def sleeper(self,counts):
        time.sleep(counts)
        return "sleeper call over, %d" %(counts)

    @restful 
    def get(self):
        # print(self.request)
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)   #return futures
        return "result",200

    def post(self):
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value) 
        return result, 200


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/hello',testRouter2),
                         (r'/', testRouter),]
        self.settings = {
            "enable_manager":1,   # if you want get the Future.result and without blocking the server. set it True
        }
        self.test = "test message"
        super(Barrel,self).__init__(self.handlers,self.settings)

    def global_test(self):
        print('global test')

if __name__ == '__main__':
    loop = Looper()
    server = loop(Barrel) or loop(handlers=[(r'/hello',testRouter2),],enable_manager=1)
    server.listen(8800)
    server.server_forever(debug=False)

```

### USAGE

```
>> curl http://127.0.0.1:8000/hello?key=5

at the same time , starting another console and input:

>> curl -XPOST http://127.0.0.1:5000/hello -d "key=5"

which means start 2 request , every request will block key=5 seconds,
but infusive thing is that both are returned at the same time.


Notice:
1. when using redirect , do not use curl for a test.

hope for enjoy!

```

### 并发测试
并发数:100

![mark](http://pacfhd1z8.bkt.clouddn.com/python/180814/cE76Cj6BiE.png?imageslim)

并发数:1000

![mark](http://pacfhd1z8.bkt.clouddn.com/python/180814/6B52FggL2D.png?imageslim)

并发数:10000

![mark](http://pacfhd1z8.bkt.clouddn.com/python/180814/gcGe28dIm5.png?imageslim)


later useage is Unfinished.

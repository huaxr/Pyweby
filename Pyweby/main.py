from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs

from core.concurrent import Executor,asyncpool
from handle.response import restful
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
        # result = self.sleeper(value)   #return futures
        return {'test':'test','test2':[1,2,3,4],'test3':{'xx':value}},200


    def post(self):
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)  # return futures
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
    server.listen(8000)
    server.server_forever(debug=False)



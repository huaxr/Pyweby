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

    def get(self):
        # print(self.request)
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)   #return futures
        # arguments = self.request.get_arguments('key','defalut get value')
        return result,200


    def post(self):
        arguments = self.request.get_arguments('key', 'defalut')
        value = int(arguments)
        result = self.sleeper(value)  # return futures
        # arguments = self.request.get_arguments('key','defalut get value')
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



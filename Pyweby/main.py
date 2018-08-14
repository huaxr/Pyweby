from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs

from core.concurrent import Executor,asyncpool
import time

class testRouter2(HttpRequest):
    executor = Executor(5)

    @asyncpool(executor=executor)
    def sleeper(self,counts):
        time.sleep(counts)
        return "sleeper call over, %d" %(counts)

    def get(self):
        # print(self.request)
        # print(self.app)
        arguments = self.request.get_arguments('key', 'defalut get value')
        value = int(arguments)
        result = self.sleeper(value)   #return futures
        # arguments = self.request.get_arguments('key','defalut get value')
        return result,200

    def post(self):
        arguments = self.request.get_arguments('key', 'defalut get value')
        value = int(arguments)
        result = self.sleeper(value)  # return futures
        # arguments = self.request.get_arguments('key','defalut get value')
        return result, 200


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/hello',testRouter2),]
        self.settings = {
            "enable_manager":True,   # if you want get the Future.result and without blocking the server. set it True
        }
        self.test = "test message"
        super(Barrel,self).__init__(self.handlers,self.settings)

    def global_test(self):
        print('global test')

if __name__ == '__main__':
    loop = Looper()
    server = loop(Barrel)
    server.listen(5000)
    server.server_forever(debug=False)



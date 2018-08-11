
from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs

class testRouter(HttpRequest):

    def get(self,request):
        #print request  #<class 'handle.request.WrapRequest'>
        print dir(request)
        print dir(self)
        arguments = request.get_arguments
        return  1222223,200
    def post(self,request):
        arguments = request.get_arguments
        return arguments, 200

class testRouter2(HttpRequest):
    # __slots__ = ['get','post']

    def get(self,request):
        arguments = request.get_arguments('key','defalut value')
        return arguments,200

    def post(self,request):
        arguments = request.get_arguments
        return arguments,200


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/',testRouter),
                    (r'/hello',testRouter2),]
        self.settings = {}
        self.test = "test message"
        super(Barrel,self).__init__(self.handlers,self.settings)

    def global_test(self):
        print 'global test'


loop = Looper() #<class 'core.select_win.SelectCycle'>

server = loop(Barrel)

server.listen(5000)
server.server_forever()



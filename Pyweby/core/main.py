from core.router import DistributeRouter
from handle.request import HttpRequest
from select_win import  SelectCycle

class testRouter(HttpRequest):
    # __slots__ = ['get','post']
    def get(self,request):
        arguments = request.get_arguments
        print arguments
        return  1222223,200
    def post(self,request):
        arguments = request.get_arguments
        return arguments, 200

class testRouter2(HttpRequest):
    # __slots__ = ['get','post']
    def get(self,request):
        print 222
        arguments = request.get_arguments
        return arguments,200

    def post(self,request):
        arguments = request.get_arguments
        return arguments





handlers = [(r'/',testRouter),(r'/hello',testRouter2)]
c = SelectCycle(handlers=handlers)
c.server_forever()



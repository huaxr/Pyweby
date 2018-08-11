# Pyweby
an awesome non-blocking web server achieved by python


### Futures
1. it's convenient to using the project to start an web application
1. it's reliable and easy deploy.
1. support concurrent flow
1. it's increaseing property and useage 


### useage

**main.py**
```
from handle.request import HttpRequest
from core.router import  Looper
from core.config import Configs

class testRouter2(HttpRequest):

    def get(self,request):
        arguments = request.get_arguments('key','defalut value')
        return arguments,200

    def post(self,request):
        arguments = request.get_arguments
        return arguments,200


class Barrel(Configs.Application):
    cls_test = 'cls test'
    def __init__(self):
        self.handlers = [(r'/hello',testRouter2),]
        self.settings = {}
        self.test = "test message"
        super(Barrel,self).__init__(self.handlers,self.settings)

    def global_test(self):
        print 'global test'


loop = Looper() 
server = loop(Barrel)
server.listen(5000)
server.server_forever()

```

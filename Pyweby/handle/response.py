from flask import json

from handle.request import HttpRequest
from handle.exc import StatusError

class HttpResponse(object):
    def __init__(self,*args,**kwargs):
        # self.status = status
        # self.headers = headers
        # self.body = body
        pass


class WrapResponse(HttpResponse):

    def __init__(self,wrapper_request):
        assert issubclass(wrapper_request.__class__,HttpRequest)
        self.wrapper = wrapper_request
        # print self.wrapper  <'HttpRequest' object at 0x48373584>  <class 'handle.request.WrapRequest'>
        self.tuples = self.wrapper.get_first_line

        self.method = self.tuples[0].lower()
        self.path = self.tuples[1]
        self.query = self.tuples[2]
        self.version = self.tuples[3]
        self.msg_pair = {200:'OK',404:'NOT FOUND',500:'SERVER ERROR'}

        super(WrapResponse,self).__init__()


    def get_writer(self):
        return self.wrapper.conn_obj

    def find_handler(self):
        return self.wrapper.find_router()


    def switch_method(self,method=None):
        '''
        here is decided to branch , the user define class has the router string , which is
        reference by this method
        :return:
        '''
        def callback(*args,**kwargs):

            return

        if method.upper() == 'GET':
            router = self.find_handler()()
            result =  getattr(router,'get')(self.wrapper)
            return result

        if method.upper() == 'POST':
            router = self.find_handler()()
            result = getattr(router, 'post')(self.wrapper)
            return result

    def discern_result(self):
        '''
        recognize the router to go, and generator response body and status!
        :return:
        '''
        result = self.switch_method(method=self.method)
        if result:
            if isinstance(result,(str,unicode,bytes)):
                body, status = result, 200
            elif isinstance(result,(tuple,list)) and len(result) == 2:
                body, status = result[0], result[1]
                assert isinstance(status,int) and  status in self.msg_pair.keys(), StatusError(status=status)
            else:
                raise Exception('no handlering')

            '''
            for return result pretty only, never user json.dumps before , otherwise status is under prase
            too
            '''
            return json.dumps(body), status


    def gen_headers(self,version, status, msg, add_header=None):
        '''
        return the headers that contains the response prefix
        '''
        header = u"{version} {status} {msg}\r\nServer: Pyweby Web 1.0".format(version=version,
                                                                                  status=status, msg=msg)
        if add_header and isinstance(header,dict):
            #TODO add header here
            pass

        return header

    def gen_body(self,  prefix=''):
        '''
        generator the body contains headers
        :param prefix: this prefix to tail whether the response package is integrity
        '''
        body, status = self.discern_result()
        msg = self.msg_pair.get(status,200)
        if prefix != u'\r\n'*2:
            return json.dumps(body)
        else:
            # print self.gen_headers(self.version, status, msg) + prefix + json.dumps(str(body))
            return self.gen_headers(self.version, status, msg) + prefix + str(body)






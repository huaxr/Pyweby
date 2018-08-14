#coding:utf-8
import re
import time

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from .exc import MethodNotAllowedException


class method_check(object):
    METHODS = ['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE']

    def __init__(self,fn):

        self.func = fn

    def __get__(self,instance,cls=None):

        if instance is None:
            return self
        res = self.func(instance)

        if len(res) > 2 and res[0] in self.METHODS:
            return res
        else:
            raise MethodNotAllowedException(method=res[1])



class HttpRequest(object):

    def __init__(self,headers=None,handlers=dict,conn =None):
        self.headers = headers
        self.handlers = handlers
        self.conn_obj = conn
        self._starttime = time.time()

        # added attribute
        self.request = None
        self.send = None
        self.app = None

    def __repr__(self):
        if self:
            return "{name}".format(name=self.__class__)

    def find_router(self):
        '''
        get_first_line has been returned by decorator, so it's changed to be a property value
        :return:
        '''
        try:
            method, path, query, version = self.get_first_line

            router = self.handlers.get(path,WrapRequest.DEFAULT_INDEX)

        except MethodNotAllowedException:

            router = WrapRequest.METHOD_NOT_ALLOWED

        return router


    def get_first_line(self):
        raise NotImplementedError

    @property
    def get_argument(self):
        '''
        phrase arguments safely
        :return:
        '''
        arguments = self.wrap_param()
        if arguments:
            tmp = []
            params = unquote(arguments).split('&')
            for i in params:
                if i:
                    tmp.append(tuple(i.split('=')))

            return self.safe_dict(tmp)

    def wrap_param(self):
        raise NotImplementedError

    def safe_dict(self,tmp):
        raise NotImplementedError


class PAGE_NOT_FOUNT(HttpRequest):
    def get(self):
        return {'404':'page not found'},404

    def post(self):
        return {'404': 'page not found'}, 404


class METHOD_NOT_ALLOWED(HttpRequest):
    def get(self):
        return {'400':'method not allowed'},400

    def post(self):
        return {'400': 'method not allowed'}, 400


class DangerousRequest(HttpRequest):

    def safe_dict(self,tmp):
        '''
        convert tmp to dict safely and avoiding raise ValueError
        :param tmp: [('a', '1'), ('c', '22222'), ('c', '222'), ('m',)]
        :return: [('a', '1'), ('c', '22222'), ('c', '222'), ('m',None)]
        '''
        if isinstance(tmp, list):
            for i in tmp:
                if len(i) != 2:
                    tmp.remove(i)
            return dict(tmp)


class WrapRequest(DangerousRequest):

    METHODS = method_check.METHODS
    DEFAULT_INDEX = PAGE_NOT_FOUNT
    METHOD_NOT_ALLOWED = METHOD_NOT_ALLOWED

    def __init__(self,headers,callback,handlers=None,application=None):
        self.headers = headers
        self.handlers = callback(handlers)
        self.application = application
        self.pair = {}
        self.regexp = re.compile(r'\r?\n')
        self.regdata = u'\r\n\r\n'
        self._has_wrapper = False
        self.router = None

        super(DangerousRequest,self).__init__(headers=self.headers,handlers=self.handlers)


    @staticmethod
    def strip_result(fn):
        def wrapper(*args,**kwargs):
            result = fn(*args,**kwargs)
            return (i.strip() for i in result)
        return wrapper


    def wrap_headers(self):
        '''
        utilize ':' symbol to split headers into key-value parameter pairs
        an keep the result in the self.pair
        :return:
        '''
        if not self._has_wrapper:
            '''
            import chardet
            encode_type = chardet.detect(html)  
            html = html.decode(encode_type['encoding'])
            
            str2bytes: encode().
            bytes2str: decode().
            '''
            try:
                headers = self.headers.decode()
            except Exception:
                headers = self.headers

            for line in self.regexp.split(headers):
                if line:
                    if ':' not in line:
                        #bug report, the uri can not contains ':'
                        self.pair['start_line'] = line
                    else:
                        attribute , parameter = line.split(':',1)
                        self.pair[attribute] = parameter.strip()
                else:
                    break
        self._has_wrapper = True
        return self.pair

    def wrap_param(self):
        '''
        parse the argument from get uri and post data
        :return:  above two
        '''
        first_line = self.get_first_line
        method = first_line[0]
        query = first_line[2]
        if method in self.METHODS:
            if method == 'GET':
                if query:
                    return query

            elif method == 'POST':
                # handing TypeError: a bytes-like object is required, not 'str' for python3
                # for Compatible with python2, try and catch
                try:
                    data = self.headers.decode().split(self.regdata,1)[1]
                except Exception:
                    data = self.headers.split(self.regdata,1)[1]

                if data:
                    return data
            else:
                raise Exception('not implement')
        else:
            raise MethodNotAllowedException(method=method)


    @method_check
    def get_first_line(self,callback=None):

        start_line = self.wrap_headers()['start_line']
        method , uri, version = start_line.split(' ')
        try:
            path, query = uri.split('?',1)
            return [i.strip() for i in (method, path, query, version)]
        except ValueError:
            return (method,uri,None,version)

    def get_attribute(self,attr):
        self.wrap_headers()
        return self.pair.get(attr,None)


    def get_arguments(self,key,default):
        '''
        wrapper of property get_argument dict.
        get value from it
        :return: key points value
        '''
        arguments = self.get_argument
        '''
        avoiding NoneType arguments
        '''
        if arguments:
            return arguments.get(key,default)







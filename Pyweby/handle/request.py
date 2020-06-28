#coding:utf-8
import json
import time
import re
import os
import threading
import warnings
import struct
import six
import hashlib

from abc import ABCMeta, abstractmethod
from collections import namedtuple
from handle.auth import Session,PRIVILIGE,user_level
from datetime import datetime,timedelta
from common.logger import init_loger,traceback
from common.exception import MethodNotAllowedException,ApplicationError,HTTPExceptions,Abort
from contextlib import contextmanager
from common.compat import bytes2str,CRLF,DCRLF,B_CRLF,\
    B_DCRLF,AND,EQUALS,SEMICOLON,STRING,_None,bytes2defaultcoding,UNQUOTE,intern,HTTPCLIENT

from util.orm_engine import sessions
from util.inspecter import set_header_check,set_headers_check ,observer_check
from config.config import Configs
from common.wrapper import method_check, _property
from handle.template import TemplateEngine as ModuleEngine
from handle.session import Sess2dict
from handle.form import Form

Session = Session()

console = Log = init_loger(__name__)

JSON = intern('application/json')
NORMAL_FORM, FILE_FORM = intern('x-www-form-urlencoded'),intern('multipart/form-data')
PLAIN, HTML = intern('text/plain'), intern('text/html')
XML = intern('text/xml')
REQUEST = intern('request')


class MetaRouter(type):
    """
    we abstract router lookup into this metaclass, making the code logic more compact,
    making request, response communication more intuitive. isn't it?
    """
    def __new__(cls, name, bases, attrs):
        def __find_handler(self):
            # if login_require setting up. checking the router and judge whether cookie is legitimate.
            router = self.wrapper.find_router()
            # if hasattr(router,'login_require'):
            #     print(dir(router))
            return router

        def __find_router(self):
            """
            get_first_line has been returned by decorator,
            so it's changed to be a property value
            """
            try:
                method, path, query, version = [bytes2str(i) for i in list(self.get_first_line)]

                tmp = cls.handler_rpc(method, path)

                if tmp:
                    return WrapRequest.RPC_ROUTER_ONLY, []

                sock_from, sock_port = self.sock.getpeername()
                # print the request log . query may be None
                if None in (method, path, version):
                    return WrapRequest.INTERNAL_SERVER_ERROR

                _log = '\t\t'.join([method, sock_from+':'+str(sock_port), path + '?' + query if query else path])
                console.info(_log)
                _match_res = MetaRouter._re_match(self.handlers, path)
                if _match_res:
                    _real_path,_re_res = _match_res
                else:
                    _real_path,_re_res = path,[]

                router = self.handlers.get(_real_path, WrapRequest.DEFAULT_INDEX)

            except MethodNotAllowedException:

                router,_re_res = WrapRequest.METHOD_NOT_ALLOWED,[]

            except Exception as e:
                Log.info(traceback(e))
                router,_re_res = WrapRequest.INTERNAL_SERVER_ERROR,[]

            return router,_re_res


        if name == intern('HttpResponse'):
            attrs['find_handler'] = __find_handler
        elif name == intern('HttpRequest'):
            attrs['find_router'] = __find_router
        else:
            pass
        return type.__new__(cls, name, bases, attrs)

    @classmethod
    def _re_match(cls,handlers,path):
        for _path in handlers.keys():
            if re.compile(_path).match(path):
                _re_ = re.compile(_path).findall(path)
                return _path,_re_

    @classmethod
    def handler_rpc(cls, method, path):
        """
        we define the router "/rpc2" as the rpc call.
        :param path:
        :return:
        """
        if path == "/rpc2" and method == "POST":
            # TODO doing the json interface.
            return 1

        else:
            return

    def get_json(self):
        raise NotImplementedError


@six.add_metaclass(MetaRouter)
class HttpRequest(HTTPExceptions):
    _aborting = Abort(extra={})

    def __init__(self,headers=None,handlers=None,sock =None):
        self.headers = headers
        self.handlers = handlers
        self.sock = sock

        self._starttime = time.time()
        # added attribute
        self.request = None
        self.app = None

    def __repr__(self):
        if self:
            return "{name}".format(name=self.__class__)

    def get_first_line(self):
        raise NotImplementedError

    @property
    def get_argument(self):
        # phrase arguments safely
        arguments = self.wrap_param()
        if arguments:
            tmp = []
            params = UNQUOTE(arguments).split(AND)
            for i in params:
                if i:
                    tmp.append(tuple(i.split(EQUALS)))

            return self.safe_dict(tmp)

    def wrap_param(self):
        raise NotImplementedError

    def safe_dict(self,tmp):
        raise NotImplementedError

    def add_cookie(self, *args, **kwargs):
        tmp = args[0]

        expires = kwargs.pop('expires', None)
        max_age = kwargs.pop('max_age', None)
        path = kwargs.pop('path', None)
        domain = kwargs.pop('domain', None)
        secure = kwargs.pop('secure', None)
        httponly = kwargs.pop('httponly', None)

        max_age = self.transe_format(max_age,type="max_age")
        expires = self.transe_format(expires,type="expires")

        if path is not None:
            path = path.encode('utf-8')

        support = {
            # Expires is used to set the expiration time of cookie,
            # and time should comply with HTTP-date specification.
            # Date: <day-name>, <day> <month> <year> <hour>:<minute>:<second> GMT
            'Expires': expires,
            # Failure time, in seconds, is not supported by low-level browsers,
            # and Max-Age priority is higher than Expires if both support
            'Max-Age': max_age,
            # The Secure property says that if a cookie is set to Secure = true,
            # the cookie can only be sent to the server using the HTTPS protocol,
            # which is not sent using the HTTP protocol.
            'Secure': secure,
            # The cookie setting HttpOnly=true can not be acquired by JS,
            #  and can not play the content of cookie with document.cookie.
            'HttpOnly': httponly,
            'Path': path,
            'Domain': domain}

        for K, V in support.items():
            if V:
                tmp.append('{key}={value}; '.format(key=K, value=V))
        cookie_jar = ''.join(tmp)
        self.__cookie_jar = cookie_jar

    def transe_format(self,msg,type=''):
        raise NotImplementedError

    def user_privilege(self,user):
        """
        given the result of a user db-query,return it's permission
        :param user: a namedtuple object. keys are ormEngine.User.__dict__

        `can_read` `can_write`  `can_upload` `is_admin`
        """

        if user and hasattr(user,'privilege'):
            priv = user_level(PRIVILIGE(user.privilege))
            return priv

    def user_priv_dict(self,user):
        '''
        in order tp generate response objects better.
        we transform them into dict format.
        '''
        tmp = {}
        NONE = self.user_privilege(user)
        tmp['is_admin'] = NONE.is_admin
        tmp['can_read'] = NONE.can_read
        tmp['can_write'] = NONE.can_write
        tmp['can_upload'] = NONE.can_upload
        return json.dumps(tmp)

    def is_admin(self,user):
        # if is admin user
        priv = self.user_privilege(user)
        if priv:
            return priv.is_admin

    def can_write(self,user):
        # if user has write privilege
        priv = self.user_privilege(user)
        if priv:
            return priv.can_write

    def can_upload(self,user):
        # if user has upload privilege
        priv = self.user_privilege(user)
        if priv:
            return priv.can_upload

    def can_read(self,user):
        # read is amost normal user privilege. default 1 for all users.
        priv = self.user_privilege(user)
        if priv:
            return priv.can_read

    @property
    def current_user(self):
        cookies = self.get_cookie()
        if cookies:
            name = cookies['name']
            priv = json.loads(cookies['level'])
            tuples = namedtuple('xx',['name','can_read','can_write','can_upload','is_admin'])
            return tuples._make([name,priv['can_read'],priv['can_write'],priv['can_upload'],priv['is_admin']])

    def _supercode(self,name):
        statement = """def {}(): return super(cls,self).func(*args,**kwargs)""".format(name)
        code = compile(statement,'statement','exec')
        return code

    def _exec(self,code):
        exec(code,{},{})

    def raise_status(self,code,*args, **kwargs):
        # return super(HttpRequest,self)._abort(*args,**kwargs)
        return self._aborting(code,*args,**kwargs)

    @set_header_check
    def set_header(self,k,v):
        with self.REQUEST as req:
            if req:
                return req.set_header(k,v)

    @set_headers_check
    def set_headers(self,dict):
        with self.REQUEST as req:
            if req:
                return req.set_headers(dict)

    def redirect(self,uri,permanent_redirect = False,status=None):
        with self.REQUEST as req:
            if req:
                return req.redirect(uri,permanent_redirect,status)

    def render(self,path,**kwargs):
        with self.REQUEST as req:
            if req:
                return req.render(path,**kwargs)

    def get_arguments(self, key, default):
        with self.REQUEST as req:
            if req:
                return req.get_arguments(key, default)

    def get_cookie(self, key=None, safe_type='session'):
        with self.REQUEST as req:
            if req:
                return req.get_cookie(key=key,safe_type=safe_type)

    def clear_cookie(self):
        with self.REQUEST as req:
            if req:
                return req._clear_cookie()

    def set_cookie(self, cookies_dict, max_age=None, expires=None,
                   path=None, domain=None, secure=False, httponly=False,
                   safe_type='session'):

        with self.REQUEST as req:
            if req:
                return req.set_cookie(cookies_dict, max_age=max_age, expires=expires,
                   path=path, domain=domain, secure=secure, httponly=httponly,
                   safe_type=safe_type)

    def _sfile(self):
        with self.REQUEST as req:
            if req and hasattr(req,'_file'):
                return req._file
            else:
                raise AttributeError('_file is not exist')

    def _sform(self):
        with self.REQUEST as req:
            if req and hasattr(req,'_form'):
                return req._form
            else:
                raise AttributeError('_form is not exist')

    def get_json(self,callback=None):
        # get the json body from the request.
        # set Content-Type: application/json
        # this will handled by this function.
        # return the correct format json or {} instead.

        # usage: curl -XPOST  http://192.168.1.3/test -H "Content-Type:application/json" -d "{\"a\":\"b\"}"
        with self.REQUEST as req:
            if req:
                return req._get_json

    def ghost(self,field_iter):

        field = tuple(map(intern, field_iter))
        arg_list = ','.join(list(field))
        tuple_new = tuple.__new__
        typename = intern(str('_'+self.__class__.__name__))

        # if PY36:
        #     s = f'def __new__(_cls, {arg_list}): return _tuple_new(_cls, ({arg_list}))'
        # else:
        #     s = 'def __new__(_cls, {arg_list}): return _tuple_new(_cls, ({arg_list}))'.format(arg_list=arg_list)

        s = 'def __new__(_cls, {}): return _tuple_new(_cls, ({}))'.format(arg_list,arg_list)

        namespace = {'_tuple_new': tuple_new, '__name__': 'namedtuple_{typename}'.format(typename=typename)}
        # exec() has the effect of interning the field names.
        # from now, namespace has attr __new__
        exec(s, namespace)

        __new__ = namespace['__new__']

        @classmethod
        def _handler(cls, iterable):
            result = tuple_new(cls, iterable)
            return result


        attrs = {
            '_handler': _handler,
            '__doc__': 'ghost object will not use the Request Handler.',
            '__slots__': (),
            '_fields': field,
            '__new__': __new__,
        }
        bases = (tuple,)
        result = type(typename,bases, attrs)
        return result


    form = property(_sform,None,None,"Form data is there is a form-type Content-Type.")
    file = property(_sfile, None, None, "File data is there is a form-type Content-Type.")

    @property
    @contextmanager
    def REQUEST(self):
        yield getattr(self, REQUEST) if hasattr(self, REQUEST) else None


class Bad_Request(HttpRequest):
    def get(self):
        return {'400':'Bad Request'},400

    def post(self):
        return {'400': 'Bad Request'},400


class Unauthorized(HttpRequest):
    def get(self):
        return {'401':'Unauthorized User'},401

    def post(self):
        return {'401': 'Unauthorized User'},401


class Forbidden(HttpRequest):
    def get(self):
        return {'403':'Forbidden'},403

    def post(self):
        return {'403': 'Forbidden'}, 403


class PAGE_NOT_FOUNT(HttpRequest):
    def get(self):
        return {'404':'page not found'},404

    def post(self):
        return {'404': 'page not found'}, 404


class METHOD_NOT_ALLOWED(HttpRequest):
    def get(self):
        return {'405':'method not allowed'},405

    def post(self):
        return {'405': 'method not allowed'}, 405


class INTERNAL_SERVER_ERROR(HttpRequest):
    def get(self):
        return {'500':'internal server error'},500

    def post(self):
        return {'500': 'internal server error'}, 500


class RPC_ROUTER_ONLY(HttpRequest):
    def get(self):
        return {'400': 'this router for rpc only'}, 400
    def post(self):
        return {'400': 'this router for rpc only'}, 400


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

    def transe_format(self,date,type=None):
        '''
        transform date from cookie's kwargs.
        the date may be expires, max-age . GMT only.
        '''
        if date is None:
            return

        if type == 'expires':
            if isinstance(date, (int,float)):
                expiration = datetime.now() + timedelta(minutes=date)
                expire = expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
                return expire

            elif isinstance(date, (datetime,timedelta)):
                return date.strftime("%a, %d-%b-%Y %H:%M:%S GMT")

            else:
                raise ValueError("unexpected date format.")

        elif type == 'max_age':
            assert isinstance(date,int)
            return int(date)

        else:
            return date

    def clear_cookie(self):
        raise NotImplementedError

    def make_warning(self,key):
        """
        warnings if needed.
        if you wanna disable warnnings. add two lines at the code beginning.

        >>> import warnings
        >>> warnings.filterwarnings("ignore")
        """
        def callback():
            warnings.warn("[*] get_arguments may invalid while content type is {}".format(self.content_type))

        if key is 1 and self.content_type:
            if not hasattr(self,'_get_arguments_enable') and 'x-www-form-urlencoded' not in self.content_type:
                callback()

        elif key is 2:
            if not hasattr(self, '_get_xml_enable'):
                callback()
        elif key is 3:
            if not hasattr(self, '_get_json_enable'):
                callback()
        elif key is 4:
            if not hasattr(self, '_get_plain_enable'):
                callback()
        else:
            pass

    def add_cookie_attribute(self,key):
        raise NotImplementedError

    def _set(self):
        raise NotImplementedError


class WrapRequest(DangerousRequest):
    METHODS = Configs.METHODS
    DEFAULT_INDEX = PAGE_NOT_FOUNT
    METHOD_NOT_ALLOWED = METHOD_NOT_ALLOWED
    INTERNAL_SERVER_ERROR = INTERNAL_SERVER_ERROR
    RPC_ROUTER_ONLY = RPC_ROUTER_ONLY

    SAFE_LOCKER = threading.RLock()

    def __init__(self,request_data,callback,handlers=None,application=None,sock=None,**kwargs):
        self.request_data = request_data

        # self.handlers = {'/index':(indexHandler, re.compile('/index'))}
        self.handlers = callback(handlers)
        self.application = application
        self.sock = sock
        self.kwargs = kwargs

        self._has_wrapper = False
        self.regexp = re.compile(CRLF)
        self.b_regexp = re.compile(B_CRLF)
        self.regdata = re.compile(DCRLF)
        self.b_regdata = re.compile(B_DCRLF)
        self.headers = self.wrap_headers(self.request_data)

        self.keep_alive = self.headers.get('Connection','')
        self.keepalive = 1 if self.keep_alive.lower() == 'keep-alive' else 0

        self.content_type = self.headers.get('Content-Type',None)
        # Classification of content-type
        if self.content_type:
            self._wrap_content_type(bytes2str(self.content_type))

        self.router = None
        self.response_header = {}
        self._status_code = 0

        super(DangerousRequest,self).__init__(headers=self.headers,handlers=self.handlers,sock = sock)

    @classmethod
    def _RE(cls, handle_dict):
        tmp = {}
        for i, j in handle_dict.items():
            tmp[i] = (j, re.compile(i))
        return tmp

    def _wrap_content_type(self,content_type):
        """
        we judge the content-type and deal with it with different handler.
        e.g. text, application ,..
        """
        if any(content_type.__contains__(x) for x in [PLAIN, HTML]):
            setattr(self,'_get_arguments_enable',1)

        # handling form data request.
        elif any(content_type.__contains__(x) for x in [NORMAL_FORM, FILE_FORM]):
            form_data = self.wrap_param()
            if form_data:
                # form is enable.
                self._form = Form(self,form_data,self.headers)
            setattr(self, '_form_enable', 1)

        elif JSON in content_type:
            are_u_json = self.wrap_param()
            try:
                self.json_content = json.loads(are_u_json)
                setattr(self, '_get_json_enable', 1)
            except json.decoder.JSONDecodeError:
                # do not raise json parse error rather than return an
                # empty dict.
                self.json_content = {}
                Log.info("[*] wrong json format: %s" % str(are_u_json))

        elif XML in content_type:
            # TODO HANDLER XML
            self.xml_content = ''
            setattr(self, '_get_xml_enable', 1)
        else:
            setattr(self, '_get_arguments_enable', 1)

    def add_cookie_attribute(self,*args,**kwargs):

        super(WrapRequest,self).add_cookie(*args,**kwargs)

    @staticmethod
    def strip_result(fn):
        def wrapper(*args,**kwargs):
            result = fn(*args,**kwargs)
            return (i.strip() for i in result)
        return wrapper

    def wrap_headers(self,bytes_header):
        # Content-Type: application / x-www-form-urlencoded
        # 8.24 add Content-Type support, form enable
        '''
        utilize ':' symbol to split headers into key-value parameter pairs
        an keep the result in the self.pair
        :return:
        '''
        if not self._has_wrapper:
            # import chardet
            # encode_type = chardet.detect(html)
            # html = html.decode(encode_type['encoding'])
            #
            # str2bytes: encode().
            # bytes2str: decode().
            try:
                headers = bytes_header.decode()
                assert not isinstance(headers,bytes),"The HTTP Request Protocol Error, SSL is disable now"
                return self.bytes_or_str(headers, str)

            except (UnicodeDecodeError,Exception):
                '''
                it may contain values that can not be decoded, and can not be 
                transferred directly to byte at str.
                '''
                headers = bytes_header
                assert isinstance(headers,bytes)
                return self.bytes_or_str(headers,bytes)

        self._has_wrapper = True

    def bytes_or_str(self,headers,type):
        tmp = {}
        if type is bytes:
            semicolon = b':'
            _re = self.b_regexp
            __re = self.b_regdata
        else:
            semicolon = ':'
            _re = self.regexp
            __re = self.regdata

        _header = __re.split(headers)[0] # split data parts. cause there may raw bytes.
        _headers = _re.split(_header)
        tmp['first_line'] = bytes2str(_headers[0])
        _headers.remove(_headers[0])
        for line in _headers:
            if line:
                if line.__contains__(semicolon):
                    attribute, parameter = line.split(semicolon, 1)
                    tmp[bytes2str(attribute)] = bytes2str(parameter.strip())
            else:
                break
        return tmp

    def wrap_param(self):
        '''
        directly retrieve the contents of the submitted query of get or post request.
        parse the argument from get uri or post data.
        :return:  above two
        '''
        first_line = self.get_first_line
        method = first_line[0]
        query = first_line[2]
        if method in self.METHODS:
            if method in ('GET',b'GET'):
                if query:
                    return query

            elif method in ('POST',b'POST'):
                # handing TypeError: a bytes-like object is required, not 'str' for python3
                # for Compatible with python2, try and catch
                try:
                    data = self.regdata.split(self.request_data.decode(),1)[1]
                except Exception:
                    # Errors like 'utf-8' codec can't decode byte 0x92 in position XXX.
                    data = self.b_regdata.split(self.request_data,1)[1]
                if data:
                    return data
            else:
                raise Exception('not implement')
        else:
            raise MethodNotAllowedException(method=method)

    @method_check
    def get_first_line(self,callback=None):
        '''
        :param callback:
        :return:
        '''
        start_line = self.headers['first_line']
        if isinstance(start_line,bytes):
            blank = b' '
            qmark = b'?'
        else:
            blank = ' '
            qmark = '?'

        assert isinstance(start_line,STRING),"[#] You may use `IE` browser, it's deny for that."

        method , uri, version = start_line.split(blank)
        try:
            path, query = uri.split(qmark,1)
            return [i.strip() for i in (method, path, query, version)]
        except ValueError:
            return (method,uri,None,version)

    def get_header_attribute(self,attr):
        return self.headers.get(attr,None)

    def get_arguments(self,key,default):
        '''
        wrapper of property get_argument dict.
        get value from it
        :return: key points value
        '''
        self.make_warning(1)
        arguments = self.get_argument
        '''
        avoiding NoneType arguments
        '''
        if arguments:
            return arguments.get(key,default)
        else:
            return default

    @property
    def args(self):
        # return an dict like object of request arguments.
        return self.get_argument

    @_property
    def get_xml(self):
        '''
        there is xml post request. you should parse that.
        :return: xml format string.
        '''
        self.make_warning(2)
        return self.xml_content if hasattr(self,'xml_content') else "<?xml></xml>"

    @_property
    def _get_json(self):
        '''
        json request handler.
        :return: an dict-like object. json.loads()
        '''
        self.make_warning(3)
        return self.json_content if hasattr(self,'json_content') else {}

    @_property
    def get_plain(self):
        '''
        plain text request.
        :return: text plain result
        '''
        self.make_warning(4)
        return self.get_argument if self.get_argument else ''

    def redirect(self, uri, permanent_redirect=False, status=None):
        # 302 header looks like:
        # HTTP/1.1 302 Moved Temporarily
        # Location: path
        if status is None:
            status = 301 if permanent_redirect else 302
        else:
            assert isinstance(status, int) and 300 <= status <= 399

        self.set_status(status)
        self.set_header("Location", uri)

    def set_status(self,code):
        self._status_code = code
        self.__status__ = 0

    def set_header(self,k,v):
        # replace if key already exists is not right.
        # http/https response header can have duplicate keys. e.g. Set-Cookie

        # am i can set_header direcly?
        if k in self.response_header:
            self.response_header[k] = self.response_header[k] + ' ' +v
        else:
            self.response_header[k] = v
            self.__header__ = 0

    def set_headers(self,dicts):
        for k, v in dicts.items():
            if k in self.response_header:
                self.response_header[k] = self.response_header[k] + ' ' + v
            else:
                self.response_header[k] = v
                self.__header__ = 0

    def render(self,path,**kwargs):
        '''
        render provides an interface to rendering Python-Object to html element.
        it's highly/extremely looks like a imitation of jinja2. it's extendable
        and you can use the code make it perfect.
        '''
        template_path = self.application.settings.get('template_path','/')
        path = os.path.join(template_path,path)
        with self.SAFE_LOCKER:
            with open(path) as fd:
                m_m = ModuleEngine(fd.read(),template_dir=template_path,file_path = path)
                res = m_m.render(kwargs)
                return res,200

    def get_cookie(self,key=None,safe_type='session'):
        '''
        get the cookie from the header's Cookies: 'xxx'
        if key provides, then return the specific value of it
        :param key: key in cookies set.
        '''
        sess = self.session
        if sess:
            if safe_type == 'session':
                if sess in Session:
                    '''
                    when debug restart the server . Session will be cleaned.
                    So , restart server will make user logout directly.
                    '''
                    res =  Session[sess]
                    return Sess2dict(res).parse

            elif safe_type == 'encrypt':
                safe_cookie_handler = self.application.settings.get('safe_cookie_handler', None)
                if not safe_cookie_handler:
                    raise ApplicationError("Error when application initilize."
                                           "when using encrypt cookie , safe_cookie_handler must be "
                                           "setted in application's settings.")

                try:
                    res =  safe_cookie_handler.decrypt(sess.encode())
                except Exception:
                    return
                temp  = res.decode()[:-2].split('&')
                tmp = {}
                for item in temp:
                    i,j = item.split('|')
                    tmp[i] = j
                if key:
                    return tmp.get(key,None)
                return tmp
        else:
            # plain cookie or None cookie header
            return sess

    def set_cookie(self, cookies_dict, max_age=None, expires=None,
                   path=None, domain=None, secure=False, httponly=False,
                   safe_type='session',permanent=False):
        '''
        :param safe: for secure reason, when secure is not setted.
        use the encryption session in place of plain cookies.

        >> usage
        token = request.headers.get('token')
        if not token:
            return {'msg': 'Unauthorized access'}, 403
        user = User.verify_auth_token(token)
        if not user:
            return {'msg': 'Unauthorized access'}, 403
        '''
        if not cookies_dict and not isinstance(cookies_dict,dict):
            return

        if safe_type == 'session':
            '''
            save the hash value of session and its corresponding state value.
            - implementation with a lightweight ORM framework.
            '''
            s = ''.join(["{key}|{value}&".format(key=key, value=value)
                            for key, value in cookies_dict.items()])[:-1]
            digest = hashlib.md5(s.encode('utf-8')).hexdigest()
            # keeping session in memory
            Session[digest] = s
            tmp = ["_session=" + digest + '; ']

            if permanent:
                '''
                for this moment. we keep the session digest in the DB for permanent.
                TODO : enhance orm to support update.
                '''
                with sessions(session=digest,value=s) as ses:
                    ses.save()

        elif safe_type == 'encrypt':
            '''
            this means using the crypto algorithm encrypt cookies and do not use database
            keeping the session.
            '''
            # TODO : this is safe session declare. you should define a cryto for that.
            safe_cookie_handler = self.application.settings.get('safe_cookie_handler',None)
            if not safe_cookie_handler:
                raise ApplicationError("Error when application initilize")
            session = ''.join(["{key}|{value}&".format(key=key, value=value)
                            for key, value in cookies_dict.items()])[:-1] + '; '
            # encrypt data using third module
            token = safe_cookie_handler.encrypt(session.encode())
            tmp = ["_session="+token.decode()+'; ']

        else:
            '''
            plain cookie is not suggest using.
            '''
            warnings.warn("[!] Plain cookie is not safe. suggeste `db_session` or `encrypt` safe_type")
            tmp = ["{key}={value}; ".format(key=key, value=value)
                   for key, value in cookies_dict.items()]

        self.add_cookie_attribute(tmp,max_age=max_age, expires=expires,
                   path=path, domain=domain, secure=secure, httponly=httponly)

        self._set()

    def _clear_cookie(self):
        '''
        reset the cookie : session=None
        '''
        sess = self.session

        if sess in Session:
            del Session[sess]

        tmp = ["_session=logout;"]
        self.add_cookie_attribute(tmp)
        self._set()

    def _set(self):
        Vampire = ''.join(['_', self.__class__.__base__.__base__.__name__, '__cookie_jar'])
        if hasattr(self, Vampire):
            self.set_header("Set-Cookie", getattr(self, Vampire))

    @property
    def session(self):
        cookies = self.get_header_attribute('Cookie')
        if cookies and "_session" in cookies:
            sess = cookies.split('=', 1)[1]
            return sess
        return cookies

    def user_privilege(self,user):
        '''
        in order to make subclassed compatible with function
        consistency
        '''
        super(WrapRequest,self).user_privilege(user)

    def current_user(self):
        # exec(self._supercode('func'),{'cls':self.__class__.__name__,'func':'current_user'})
        # a = func()
        return super(WrapRequest,self).current_user

    def raise_status(self,code,*args,**kwargs):
        return super(WrapRequest, self).raise_status(code)


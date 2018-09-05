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

from util.Engines import BaseEngine
from collections import namedtuple
from handle.auth import Session,PRIVILIGE,user_level
from core.config import Configs
from datetime import datetime,timedelta
from util.logger import init_loger,traceback
from .exc import MethodNotAllowedException,ApplicationError,HTTPExceptions,Abort
from contextlib import contextmanager
from util._compat import bytes2str,CRLF,DCRLF,B_CRLF,\
    B_DCRLF,AND,EQUALS,SEMICOLON,STRING,_None,bytes2defaultcoding,UNQUOTE,intern,PY36

from util.ormEngine import sessions



Session = Session()

console = Log = init_loger(__name__)


class Sess2dict(object):
    def __init__(self,sess):
        self.sess = sess

    @property
    def parse(self):
        res = {}
        tmp = self.sess.split('&')
        for i in tmp:
            k,v = i.split('|')
            res[k] = v
        return res

def ExceptHandler(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            Log.critical(traceback(e))
            return None
    return wrapper


class BaseCookie(type):
        pass


class Header(object):
    def __init__(self):
        raise NotImplementedError

    def ExceptHandler(self):
        pass

class _property(property):
    '''
    wrapped magic.

    '''
    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

        super(_property,self).__init__()


    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value


    def __get__(self, instance, owner=None):

        '''
        keeping the result in the obj.__dict__.
        __dict__ is instance's bindings. so, this make keeping result
        and don't need call method twice.

        >>> class Test(object):
        >>>    @_property
        >>>    def func(self):
        >>>       self.name = 111
        >>>        a = 1
        >>>        b = 2
        >>>        return a+b

        >>> a = Test()
        >>> c = a.func
        >>> print(a.__dict__)
        :return: {'func': 3}
        '''
        if instance is None:
            return self
        value = instance.__dict__.get(self.__name__, _None)
        if value is _None:
            value = self.func(instance)
            instance.__dict__[self.__name__] = value
        return value



class File(object):
    '''
    request.file
    the properties of a file upload operation from which you can access the properties
    of a file object, such as filename, type of upload, hexadecimal ,and so on.

    '''
    __slots__  = ['info','raw',"filename","name"]

    def __init__(self,file_info=None,file_raw=None):
        self.info = file_info
        self.raw = file_raw

    def __getattribute__(self, item):
        item = item.lower()
        tmp = {}

        if item in ('filename','name'):
            info = self.info.get('Content-Disposition',None)
            for _item in info.split(SEMICOLON):
                if EQUALS in _item:
                    k,v = _item.split(EQUALS)
                    tmp[k.strip()] = v.strip('"')
            return tmp.get(item,_None)

        return object.__getattribute__(self, item)


    @ExceptHandler
    def saveto(self,path):
        '''
        save the File object's raw_data to a path.

        raw_data has two station:
        1. application/octet-stream
        2. application/text-plain
        the two states are properly handled here, Is there still bug?
        :param path: the path you wanner to save it.
        :return: None
        '''

        if path and os.path.exists(os.path.dirname(path)):
            if isinstance(self.raw, bytes):
                with open(path, 'wb+') as f:
                    _hex = self.raw.hex()
                    for i in range(int(len(_hex) / 4)):
                        hex = int(str(_hex[i*4:i*4+4]),16)
                        f.write(struct.pack(">H",hex))
            else:
                with open(path, 'w+') as f:
                    f.write(self.raw)
        else:
            Log.info("[!] file [%s] path is illegal" %path)
            return

    def make_secure_name(self):
        _file = self.filename



    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __repr__(self):
        return self.__doc__ if hasattr(self,'__doc__') \
            else 'the properties of a file upload operation from ' \
                                                            'which you can access the properties ' \
                                                            'of a file object, such as filename, type of ' \
                                                            'upload, hexadecimal ,and so on.'

class BaseForm(object):

    def __repr__(self):
        return "Correctly handle the form parameters of the HTTP request, " \
               "and classify the information according to the content-type field."


class Form(BaseForm):

    def __init__(self,WrapRequest,form_data,headers_dict):
        self.WrapRequest = WrapRequest
        self.form_data = form_data
        self.headers_dict = headers_dict
        self.form_type = bytes2str(self.headers_dict.get('Content-Type','application'))
        self.content_length = self.headers_dict.get('Content-Length',0)

        if  'boundary' in self.form_type:
            self.boundary = '--'+self.form_type.split('boundary=')[1]

        '''
        # form_type also means enctype , just like this below
        # <form method=post enctype='multipart/form-data'>
        The browser encapsulates form data into HTTP body or URL, 
        and then sends it to server. If there is no type=file control,
         use the default application/x-www-form-urlencoded. 
         But if there is type=file, multipart/form-data is needed. 
         
         When the action is post and the Content-Type type is multipart/form-data, 
         the browser splits the entire form as a control, 
         adding information such as Content-Disposition (form-data or file),
         Content-Type (default text/plain), name (control name),
        and a boundary to each part. 

        '''
        if self.form_type == 'application/x-www-form-urlencoded':

            tmp = self.parse
            for item in tmp:
                # if a malicious attacker uses -d "x" instead of -d "x=x"
                if len(item) == 2:
                    i, j = item
                    setattr(self,i,j)

        elif self.form_type.startswith('multipart'):
            # 'multipart/form-data'
            # a small file upload header looks like this:
            '''
            POST/upload HTTP/1.1 
        　　Content-Type: multipart/form-data;boundary=-----------------------------7db372eb000e2
        　　Content-Length: 3693

　　        -------------------------------7db372eb000e2
　　        Content-Disposition: form-data; name="file"; filename="kn.jpg"\r\n
　　        Content-Type: image/jpeg\r\n
            \r\n
            binary...data...\r\n
　　        -------------------------------7db372eb000e2--\r\n 
            '''
            if self.boundary:
                if isinstance(self.form_data,str):
                    _re = re.compile(self.boundary)
                    __re = re.compile(CRLF)
                    ___re = re.compile(DCRLF)
                    pieces = _re.split(self.form_data)
                    tmp = {}
                    for i in pieces:
                        if i:
                            core_ = ___re.split(i)
                            if len(core_) == 2:
                                form_data_info,form_data_raw = core_
                                info_ = __re.split(form_data_info.strip())
                                for i in info_:
                                    if i.__contains__(':'):
                                        b_key, b_value = i.split(':',1)
                                        if b_key in ('Content-Disposition','Content-Type'):
                                            tmp[b_key] = b_value

                                self.form_data_info = tmp
                                self.form_data_raw = form_data_raw.strip()


                elif isinstance(self.form_data,bytes):
                    _re = re.compile(self.boundary.encode())
                    __re = re.compile(B_CRLF)
                    ___re = re.compile(B_DCRLF)
                    pieces = _re.split(self.form_data)
                    tmp = {}

                    for i in pieces:
                        if i :
                            core_ = ___re.split(i)
                            if len(core_) == 2:
                                form_data_info, form_data_raw = core_
                                info_ = __re.split(form_data_info.strip())
                                for i in info_:
                                    if i.__contains__(b':'):
                                        b_key, b_value = i.split(b':', 1)
                                        if b_key in (b'Content-Disposition', b'Content-Type'):
                                            # chinese character will raise Exception.
                                            try:
                                                tmp[bytes2str(b_key)] = bytes2defaultcoding(b_value)
                                            except Exception as e:
                                                Log.critical(traceback(e))

                                self.form_data_info = tmp
                                self.form_data_raw = form_data_raw.strip()

                else:
                    raise TypeError('No Handling.')
        else:
            raise TypeError('No Handling.')
        # print(self.form_data_info)
        # print(self.form_data_raw)
        self.binding_file()


    def binding_file(self):
        if hasattr(self,'form_data_info'):
            with File(self.form_data_info,self.form_data_raw) as _f:
                setattr(self.WrapRequest,'_file',_f)


    @property
    def parse(self):
        tmp = []
        params = UNQUOTE(self.form_data).split('&')
        for i in params:
            if i:
                tmp.append(tuple(i.split('=')))
        return tmp


class MetaRouter(type):
    '''
    we abstract router lookup into this metaclass, making the code logic more compact,
    making request, response communication more intuitive. isn't it?
    '''
    def __new__(cls, name, bases, attrs):

        def __find_handler(self):
            # if login_require setting up. checking the router and judge whether cookie is legitimate.
            router = self.wrapper.find_router()
            # if hasattr(router,'login_require'):
            #     print(dir(router))
            return router

        def __find_router(self):
            '''
            get_first_line has been returned by decorator,
            so it's changed to be a property value
            :return:
            '''
            try:
                method, path, query, version = [bytes2str(i) for i in list(self.get_first_line)]
                sock_from, sock_port = self.sock.getpeername()
                # print the request log . query may be None
                if None in (method, path, version):
                    return WrapRequest.INTERNAL_SERVER_ERROR

                _log = '\t\t'.join([method, sock_from, path + '?' + query if query else path])
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
    def _re_matcher(cls,handlers,path):
        for _path, _obj in handlers.items():
            xx = re.compile(_path).findall(path)

class method_check(object):

    def __init__(self,fn):

        self.func = fn


    def __contains__(self, item):
        return item in Configs.METHODS


    def __get__(self,instance,cls=None):

        if instance is None:
            return self
        res = self.func(instance)

        if len(res) > 2 and res[0] in self:
            return res
        else:
            Log.info("raise MethodNotAllowedException")
            raise MethodNotAllowedException(method=res[1])


class Builder(object):
    STEPER = 1

    def __init__(self, indent=0):
        # record the steps
        self.indent = indent
        # save code line by line in this list
        self.lines = []

    def goahead(self):
        self.indent += self.STEPER

    def goback(self):
        self.indent -= self.STEPER

    def add(self, code):
        self.lines.append(code)

    def add_line(self, code):
        self.lines.append('\t' * self.indent + code)

    def __str__(self):
        return '\n'.join(map(str, self.lines))

    def __repr__(self):
        return str(self)


class TemplateEngine(BaseEngine):
    '''
    Template Parse Engine.
    Reference:
    1: Tornado source code
    2: uri: http://python.jobbole.com/85155/
    '''

    def __init__(self, raw_html, template_dir='', file_path='', global_locals=None, indent=0,
                 magic_func='__exists_func', magic_result='__exists_list'):
        self.raw_html = raw_html
        self.template_dir = template_dir
        self.file_path = file_path
        self.buffered = []
        self.magic_func = magic_func
        self.magic_result = magic_result

        # for user define namespace
        self.global_locals = global_locals or {}

        self.encoding = 'utf-8'
        self.builder = Builder(indent=indent)
        self.__generate_python_func()
        super(TemplateEngine, self).__init__(self.raw_html)


    def render(self, kwargs):
        _ignore = kwargs.pop('ignore_cache', False)
        # add defined namespace first
        kwargs.update(self.global_locals)

        '''
        if ignore cache then(when _ignore is True). find the cache dict value 
        and return object if cache exist else do the compile.
        '''
        if _ignore or self.file_path not in BaseEngine._template_cache:
            co = compile(str(self.builder), self.file_path, 'exec')
            BaseEngine._template_cache[self.file_path] = co
        else:
            co = BaseEngine._template_cache[self.file_path]

        __ = self.safe_exec(co, kwargs)
        if __ is not None:
            return ''

        result = kwargs[self.magic_func]()
        return result


    def __generate_python_func(self):
        builder = self.builder
        builder.add_line('def {}():'.format(self.magic_func))
        builder.goahead()
        builder.add_line('{} = []'.format(self.magic_result))
        self._parse()
        self.clear_buffer()
        builder.add_line('return "".join({})'.format(self.magic_result))
        builder.goback()

    def clear_buffer(self):
        line = '{0}.extend([{1}])'.format(self.magic_result, ','.join(self.buffered))
        self.builder.add_line(line)
        self.buffered = []

    def _handle_variable(self, token):
        """variable handler"""
        variable = token.strip(' {} ')
        # >>> {{ title }} ->  title
        self.buffered.append('str({})'.format(variable))

    def _handle_comment(self, token):
        """annotation handler"""
        pass

    def _handle_string(self, token):
        """string handler"""
        '''
        handler default values, which may contains whitespace word,
        using strip() eliminate them.
        '''
        self.buffered.append('{}'.format(repr(token.strip())))

    def _handle_tag(self, token):
        """
        tag handler
        when calling this , you should save the code generate before
        and clear the self.buffer for the next Builder's code.
        """
        self.clear_buffer()

        tag = token.strip(' {%} ')
        tag_name = tag.split()[0]
        # tag: if score > 88
        # tag_name: if

        if tag_name == 'include':
            self._handle_include(tag)
        else:
            self._handle_statement(tag, tag_name)

    def _handle_statement(self, tag, tag_name):
        """handler if/elif/else/for/break"""
        if tag_name in ('if', 'elif', 'else', 'for'):
            if tag_name in ('elif', 'else'):
                self.builder.goback()
            self.builder.add_line('{}:'.format(tag))
            self.builder.goahead()

        elif tag_name in ('break',):
            self.builder.add_line(tag)

        elif tag_name in ('endif', 'endfor'):
            self.builder.goback()

    def _handle_include(self, tag):
        '''
        The include tag acts like rendering another template using the namespace
        where the include is located and then using the rendered result.

        So we can treat the include template file as a normal template file,
        replace the include location with the code generated by parsing that template,
        and append the result to `__exists_list`.
        '''

        filename = tag.split()[1].strip('"\'')  # index.html
        included_template = self._parse_template_file(filename)
        self.builder.add(included_template.builder)
        self.builder.add_line(
            '{0}.append({1}())'.format(
                self.magic_result, included_template.magic_func
            )
        )

    def _parse_template_file(self, filename):
        template_path = os.path.realpath(
            os.path.join(self.template_dir, filename)
        )
        name_suffix = str(hash(template_path)).replace('-', '_')
        # in the main function generate another function which return call
        # will append into the self.builder
        magic_func = '{}_{}'.format(self.magic_func, name_suffix)
        magic_result = '{}_{}'.format(self.magic_result, name_suffix)
        # recursion the Module to generate the small part include.
        with open(template_path, encoding=self.encoding) as fp:
            template = self.__class__(
                fp.read(), indent=self.builder.indent,
                global_locals=self.global_locals,
                magic_func=magic_func, magic_result=magic_result,
                template_dir=self.template_dir
            )
        return template

    def _handle_extends(self):
        match_extends = self.re_extends.match(self.raw_html)

        if match_extends is None:
            return

        parent_template_name = match_extends.group('name').strip('"\' ')  # return extends.html
        parent_template_path = os.path.join(
            self.template_dir, parent_template_name
        )
        # get all the block in the template
        child_blocks = self._get_all_blocks(self.raw_html)

        with open(parent_template_path, encoding=self.encoding) as fp:
            parent_text = fp.read()
        new_parent_text = self._replace_parent_blocks(parent_text, child_blocks)
        # print(new_parent_text)
        # child_header {{ block.super }}
        # parent_footer
        self.raw_html = new_parent_text

    def _replace_parent_blocks(self, parent_text, child_blocks):

        def replace(match):
            name = match.group('name')
            parent_code = match.group('code')
            child_code = child_blocks.get(name, '')
            # return child_code or parent_code
            child_code = self.re_block_super.sub(parent_code, child_code)
            new_code = child_code or parent_code
            return new_code

        return self.re_blocks.sub(replace, parent_text)

    def _get_all_blocks(self, text):
        # print(self.re_blocks.findall(text))
        # [('header', ' child_header {{ block.super }} ')]
        return {name: code for name, code in self.re_blocks.findall(text)}


extra = {}
ModuleEngine = TemplateEngine
_abortting = Abort(extra=extra)



@six.add_metaclass(MetaRouter)
class HttpRequest(HTTPExceptions):
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
        '''
        phrase arguments safely
        :return:
        '''
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
        '''
        given the result of a user db-query,return it's permission
        :param user: a namedtuple object. keys are ormEngine.User.__dict__

        `can_read` `can_write`  `can_upload` `is_admin`
        '''

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
        return _abortting(code,*args,**kwargs)


    def set_header(self,k,v):
        with self.REQUEST as req:
            if req:
                return req.set_header(k,v)

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

        s = 'def __new__(_cls, {arg_list}): return _tuple_new(_cls, ({arg_list}))'.format(arg_list=arg_list)

        namespace = {'_tuple_new': tuple_new, '__name__': 'namedtuple_{typename}'.format(typename=typename)}
        # exec() has the effect of interning the field names.
        # from now, namespace has attr __new__
        exec(s, namespace)

        __new__ = namespace['__new__']

        @classmethod
        def _handler(cls, iterable):
            result = tuple_new(cls, iterable)
            return result

        def befor_request():
            pass


        def after_request():
            pass

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
        yield getattr(self,'request') if hasattr(self,'request') else None


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
        '''
        warnings if needed.
        if you wanna disable warnnings. add two lines at the code beginning.

        >>> import warnings
        >>> warnings.filterwarnings("ignore")
        '''
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
        self.content_type =  self.headers.get('Content-Type',None)
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
        '''
        we judge the content-type and deal with it with different handler.
        e.g. text, application ,..
        :return:  None
        '''
        if any(content_type.__contains__(x) for x in ['text/plain','text/html']):
            setattr(self,'_get_arguments_enable',1)

        # handling form data request.
        elif any(content_type.__contains__(x) for x in ['x-www-form-urlencoded','multipart/form-data']):
            form_data = self.wrap_param()
            if form_data:
                # form is enable.
                self._form = Form(self,form_data,self.headers)
            setattr(self, '_form_enable', 1)

        elif 'application/json' in content_type:
            are_u_json = self.wrap_param()
            try:
                self.json_content =  json.loads(are_u_json)
                setattr(self, '_get_json_enable', 1)
            except json.decoder.JSONDecodeError:
                # do not raise json parse error rather than return an
                # empty dict.
                self.json_content =  {}
                Log.info("[*] wrong json format: %s" %str(are_u_json))


        elif 'text/xml' in content_type:
            # TODO HANDLER XML
            self.xml_content = ''
            setattr(self, '_get_xml_enable', 1)
        else:
            setattr(self, '_get_arguments_enable', 1)


    # def __setattr__(self, key, value):
    #     print(key,value)
    #     setattr(self, key, value)

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

    def redirect(self,uri,permanent_redirect = False,status=None):
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

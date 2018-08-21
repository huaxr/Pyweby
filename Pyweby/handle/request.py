#coding:utf-8
import time
import re
import os
import threading

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from .exc import MethodNotAllowedException
from util.Engines import BaseEngine
from util.logger import init_loger,traceback

console = Log = init_loger(__name__)

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


ModuleEngine = TemplateEngine


class HttpRequest(object):

    def __init__(self,headers=None,handlers=dict,sock =None):
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

    def find_router(self):
        '''
        get_first_line has been returned by decorator, so it's changed to be a property value
        :return:
        '''
        try:
            method, path, query, version = self.get_first_line
            sock_from, sock_port = self.sock.getpeername()

            # print the request log .
            _log = '\t\t'.join([method,path,':'.join([sock_from,str(sock_port)])])
            console.info(_log)

            router = self.handlers.get(path,WrapRequest.DEFAULT_INDEX)

        except MethodNotAllowedException:

            router = WrapRequest.METHOD_NOT_ALLOWED

        except Exception:

            router = WrapRequest.INTERNAL_SERVER_ERROR

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


    def render(self,*args,**kwargs):
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

class INTERNAL_SERVER_ERROR(HttpRequest):
    def get(self):
        return {'400':'internal server error'},500

    def post(self):
        return {'400': 'internal server error'}, 500

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
    INTERNAL_SERVER_ERROR = INTERNAL_SERVER_ERROR
    SAFE_LOCKER = threading.Lock()

    def __init__(self,request_data,callback,handlers=None,application=None,sock=None):
        self.request_data = request_data
        self.handlers = callback(handlers)

        self.application = application
        self.sock = sock

        self._has_wrapper = False
        self.regexp = re.compile(r'\r?\n')
        self.regdata = u'\r\n\r\n'

        self.headers = self.wrap_headers(self.request_data)
        self.router = None

        super(DangerousRequest,self).__init__(headers=self.headers,handlers=self.handlers,sock = sock)


    @staticmethod
    def strip_result(fn):
        def wrapper(*args,**kwargs):
            result = fn(*args,**kwargs)
            return (i.strip() for i in result)
        return wrapper


    def wrap_headers(self,bytes_header):
        tmp = {}
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
                headers = bytes_header.decode()
                assert not isinstance(headers,bytes),"The HTTP Request Protocol Error, SSL is disable now"
            except Exception as e:
                Log.info(traceback(e))
                headers = bytes_header
                assert not isinstance(headers, bytes),"The HTTP Request Protocol Error, SSL is disable now"

            for line in self.regexp.split(headers):
                if line:
                    if ':' not in line:
                        #bug report, the uri can not contains ':'
                        tmp[u'first_line'] = line
                    else:
                        attribute , parameter = line.split(':',1)
                        tmp[attribute] = parameter.strip()
                else:
                    break
        self._has_wrapper = True

        return tmp

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
                    data = self.request_data.decode().split(self.regdata,1)[1]
                except Exception:
                    data = self.request_data.split(self.regdata,1)[1]

                if data:
                    return data
            else:
                raise Exception('not implement')
        else:
            raise MethodNotAllowedException(method=method)


    @method_check
    def get_first_line(self,callback=None):
        start_line = self.headers['first_line']
        assert isinstance(start_line,str),"[#] You may use `IE` browser, it's deny for that."
        method , uri, version = start_line.split(' ')
        try:
            path, query = uri.split('?',1)
            return [i.strip() for i in (method, path, query, version)]
        except ValueError:
            return (method,uri,None,version)

    def get_attribute(self,attr):
        return self.headers.get(attr,None)


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
        else:
            return default


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

    def set_header(self,k,v):
        self.response_header = {k:v}


    def render(self,path,**kwargs):

        template_path = self.application.settings.get('template_path','/')
        path = os.path.join(template_path,path)
        with self.SAFE_LOCKER:
            with open(path) as fd:
                m_m = ModuleEngine(fd.read(),template_dir=template_path,file_path = path)
                res = m_m.render(kwargs)
                return res,200

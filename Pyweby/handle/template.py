#coding: utf-8
import re
import types
import os

class BaseEngine(object):
    WHATEVER = 0
    _template_cache = {}
    re_variable = re.compile(r'\{\{ .*? \}\}')
    re_comment = re.compile(r'\{# .*? #\}')
    re_tag = re.compile(r'\{% .*? %\}')

    re_extends = re.compile(r'\{% extends (?P<name>.*?) %\}')
    re_blocks = re.compile(
        r'\{% block (?P<name>\w+) %\}'
        r'(?P<code>.*?)'
        r'\{% endblock \1 %\}', re.DOTALL)
    re_block_super = re.compile(r'\{\{ block\.super \}\}')
    re_tokens = re.compile(r'((?:\{\{ .*? }\})|(?:\{\# .*? \#\}|(?:\{% .*? %\})))', re.X)

    def __init__(self, raw_html):
        self.raw_html = raw_html

    def _parse(self):

        self._handle_extends()
        tokens = self.re_tokens.split(self.raw_html)
        # ['<h1>', '{% if score >= 80 %}', ' A\n   ', '{% elif score >= 60 %}',
        # ' B\n   ', '{% else %}', ' C\n   ', '{% endif %}', '</h1>']

        handlers = (
            (self.re_variable.match, self._handle_variable),  # {{ variable }}
            (self.re_tag.match, self._handle_tag),  # {% tag %}
            (self.re_comment.match, self._handle_comment),  # {# comment #}
        )
        default_handler = self._handle_string  # normal string

        for token in tokens:
            for match, handler in handlers:
                if match(token):
                    handler(token)
                    break
            else:
                default_handler(token)

    def _handle_variable(self, token):
        """variable handler"""
        raise NotImplementedError

    def _handle_comment(self, token):
        """annotation handler"""
        raise NotImplementedError

    def _handle_string(self, token):
        """string handler"""
        raise NotImplementedError

    def _handle_tag(self, tag):
        raise NotImplementedError

    def _handle_extends(self):
        raise NotImplementedError

    def safe_exec(self, co, kw):
        assert isinstance(co, types.CodeType)
        '''
        every user control value should be sterilize/disinfect here.
        '''
        # for i in kw.values():
        #     if '__import__' in i:
        #         # raise DangerTemplateError('malicious code found.')
        #         return self.WHATEVER
        exec(co, kw)

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

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
from core.engines import BaseEngine
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
from common.wrapper import method_check, except_handler
from handle.file import File
Session = Session()

console = Log = init_loger(__name__)

class BaseForm(object):

    def __repr__(self):
        return "Correctly handle the form parameters of the HTTP request, " \
               "and classify the information according to the content-type field."

class Form(BaseForm):

    def __init__(self ,WrapRequest ,form_data ,headers_dict):
        self.WrapRequest = WrapRequest
        self.form_data = form_data
        self.headers_dict = headers_dict
        self.form_type = bytes2str(self.headers_dict.get('Content-Type' ,'application'))
        self.content_length = self.headers_dict.get('Content-Length' ,0)

        if  'boundary' in self.form_type:
            self.boundary = '-- ' +self.form_type.split('boundary=')[1]

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
                    setattr(self ,i ,j)

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
                if isinstance(self.form_data ,str):
                    _re = re.compile(self.boundary)
                    __re = re.compile(CRLF)
                    ___re = re.compile(DCRLF)
                    pieces = _re.split(self.form_data)
                    tmp = {}
                    for i in pieces:
                        if i:
                            core_ = ___re.split(i)
                            if len(core_) == 2:
                                form_data_info ,form_data_raw = core_
                                info_ = __re.split(form_data_info.strip())
                                for i in info_:
                                    if i.__contains__(':'):
                                        b_key, b_value = i.split(':' ,1)
                                        if b_key in ('Content-Disposition' ,'Content-Type'):
                                            tmp[b_key] = b_value

                                self.form_data_info = tmp
                                self.form_data_raw = form_data_raw.strip()

                elif isinstance(self.form_data ,bytes):
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
        if hasattr(self ,'form_data_info'):
            with File(self.form_data_info ,self.form_data_raw) as _f:
                setattr(self.WrapRequest ,'_file' ,_f)

    @property
    def parse(self):
        tmp = []
        params = UNQUOTE(self.form_data).split('&')
        for i in params:
            if i:
                tmp.append(tuple(i.split('=')))
        return tmp
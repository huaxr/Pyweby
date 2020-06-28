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

Session = Session()

console = Log = init_loger(__name__)

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

    @except_handler
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

#coding: utf-8
import ssl
import sys
from common.dict import Globals


class Configs(object):
    PY3 = sys.version_info >= (3,)
    METHODS = ['GET', 'POST', b'GET', b'POST', 'OPTIONS', 'PUT', 'DELETE', b'OPTIONS', b'PUT', b'DELETE']
    V23 = ssl.PROTOCOL_SSLv23
    R = 0x01
    W = 0x04
    E = 0x08
    M = 0x0F  # for main socket


Global = Globals()
Global += {"DATABASE": "mysql://127.0.0.1:3306/test?user=root&passwd=787518771"}
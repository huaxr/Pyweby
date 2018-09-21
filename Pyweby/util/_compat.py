import sys
import os
import socket

PY36 = sys.version_info >= (3, 6)
py33 = sys.version_info >= (3, 3)
py32 = sys.version_info >= (3, 2)
py3k = sys.version_info >= (3, 0)
py2k = sys.version_info < (3, 0)
py265 = sys.version_info >= (2, 6, 5)
jython = sys.platform.startswith('java')
pypy = hasattr(sys, 'pypy_version_info')
win32 = sys.platform.startswith('win')
cpython = not pypy and not jython

PY3 = sys.version_info >= (3,)
PY2 = sys.version_info < (3, 0)

if sys.platform != 'darwin':
    # mac os will raise
    # when using `socket.gethostbyname(socket.gethostname())`
    # socket.gaierror: [Errno 8] nodename nor servname provided, or not known
    HOSTNAME = socket.gethostname()
else:
    HOSTNAME = 'localhost' or ''


if hasattr(os,'cpu_count'):
    COUNT = (os.cpu_count() or 1) * 5
else:
    COUNT = 10

if PY3:
    STRING = (str,bytes)
    from urllib.parse import urlparse,unquote
    from urllib import request
    from functools import reduce
    from sys import intern  # intern str operation. differ from py2

    REDUCE = reduce
    URLPARSE = urlparse
    UNQUOTE = unquote
    EXCEPTION_MSG = lambda e: e.args
    intern = intern
    HTTPCLIENT = request
    

else:
    import urllib2 as HTTPCLIENT
    from urlparse import urlparse, unquote
    STRING = (str, unicode, bytes)
    REDUCE = reduce
    URLPARSE = urlparse
    UNQUOTE = unquote
    EXCEPTION_MSG = lambda e: e.message
    intern = intern
    HTTPCLIENT = HTTPCLIENT
    # req = REQUEST.Request(url='%s%s%s' % (url,'?',textmod),headers=header_dict)
    # REQUEST.urlopen(req)

class _None(object):

    def __repr__(self):
        return 'NoneObject'

    def __reduce__(self):
        return 'NoneObject is not reduce'

_None = _None()
SET = setattr
HAS = hasattr
CODING = sys.getdefaultencoding()

bytes2str = lambda x: x.decode() if isinstance(x,bytes) else x
str2bytes = lambda x:x.encode() if isinstance(x,str) else x

SYSTEM = sys.platform
if SYSTEM.startswith('win'):
    bytes2defaultcoding = lambda x: x.decode('gbk') if isinstance(x,bytes) else x
else:
    bytes2defaultcoding = lambda x: x.decode('utf-8') if isinstance(x, bytes) else x

CRLF = "\r\n"
B_CRLF = b"\r\n"
DCRLF = "\r\n\r\n"
B_DCRLF = b"\r\n\r\n"
AND = '&'
EQUALS = '='
SEMICOLON = ';'


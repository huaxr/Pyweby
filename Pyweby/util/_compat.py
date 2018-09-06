import sys
import os

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

if hasattr(os,'cpu_count'):
    COUNT = (os.cpu_count() or 1) * 5
else:
    COUNT = 10

if PY3:
    STRING = (str,bytes)
    from urllib.parse import urlparse,unquote
    from functools import reduce
    from sys import intern  # intern str operation. differ from py2
    REDUCE = reduce
    URLPARSE = urlparse
    UNQUOTE = unquote
    EXCEPTION_MSG = lambda e: e.args
    intern = intern

else:
    STRING = (str, unicode,bytes)
    from urlparse import urlparse, unquote
    REDUCE = reduce
    URLPARSE = urlparse
    UNQUOTE = unquote
    EXCEPTION_MSG = lambda e: e.message
    intern = intern

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


import sys
import os
PY3 = sys.version_info >= (3,)

if hasattr(os,'cpu_count'):
    COUNT = (os.cpu_count() or 1) * 5
else:
    COUNT = 10

if PY3:
    STRING = (str,bytes)
    from urllib.parse import urlparse,unquote
    from functools import reduce
    REDUCE = reduce
    URLPARSE = urlparse
    UNQUOTE = unquote

else:
    STRING = (str, unicode,bytes)
    from urllib import urlparse, unquote
    REDUCE = reduce
    URLPARSE = urlparse
    UNQUOTE = unquote

class _None(object):

    def __repr__(self):
        return 'NoneObject'

    def __reduce__(self):
        return 'NoneObject is not reduce'

_None = _None()

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



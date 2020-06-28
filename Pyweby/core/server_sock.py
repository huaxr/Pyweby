#coding:utf-8
import ssl
import socket
from common.logger import Logger
from common.compat import HOSTNAME
from common.config import Configs
try:
    from os import uname
except Exception:
    from platform import uname

Log = Logger(__name__)


class SSLSocket(object):

    def __init__(self,context,conn,cert,key):
        self.context = context
        self.conn = conn
        self.cert = cert
        self.key = key

    def ssl_py3_context(self):
        stream =  self.context.wrap_socket(self.conn,server_side=True)
        return stream

    def ssl_py2_context(self):
        stream = ssl.wrap_socket(self.conn,self.key,self.cert,server_side=True,ssl_version=ssl.PROTOCOL_SSLv23)
        return stream

    def ssl_context(self):
        if Configs.PY3:
            return self.ssl_py3_context()
        else:
            return self.ssl_py2_context()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def gen_socket(port=None,ssl_enable=False):
    HOST = socket.gethostbyname(HOSTNAME)
    PORT = 443 if ssl_enable else 80
    PORT = port or PORT
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM,0)
        s.bind((HOST, PORT))
        s.listen(1)
    except socket.error as e:
        Log.critical("[*] Server Socket occupation conflict")
        raise e
    Log.info("[*] Hello, {}@Pyweby master.".format(socket.gethostname() or uname().node))
    Log.info("[*] Server %s://%s:%d started! fd=[%s]" %("https" if ssl_enable else "http", HOST, PORT, s.fileno()))
    return s


#coding:utf-8

import ssl
import socket
from .config import Configs
from util.logger import Logger

Log = Logger(__name__)


def ssl_context(options_ssl):
    if isinstance(options_ssl, ssl.SSLContext):
        return options_ssl

    # using ssl.PROTOCOL_SSLv23 by default
    context = ssl.SSLContext(
        options_ssl.get('ssl_version', ssl.PROTOCOL_SSLv23))
    # analysis ssl options
    if 'certfile' in options_ssl:
        context.load_cert_chain(options_ssl['certfile'], options_ssl.get('keyfile', None))
    if 'cert_reqs' in options_ssl:
        context.verify_mode = options_ssl['cert_reqs']
    if 'ca_certs' in options_ssl:
        context.load_verify_locations(options_ssl['ca_certs'])
    if 'ciphers' in options_ssl:
        context.set_ciphers(options_ssl['ciphers'])

    if hasattr(ssl, 'OP_NO_COMPRESSION'):
        context.options |= ssl.OP_NO_COMPRESSION
    # ssl context generated, return it to wrapper socket to support ssl
    return context


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
        stream = ssl.wrap_socket(self.conn,self.cert,self.key,server_side=True,ssl_version=ssl.PROTOCOL_SSLv23)
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


def gen_serversock(port=None,ssl_enable=False):
    HOST = socket.gethostbyname(socket.gethostname()) or '127.0.0.1'
    # HOST = "127.0.0.1"
    PORT = 443 if ssl_enable else 80
    PORT = port or PORT
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM,0)
        s.bind((HOST, PORT))
        s.listen(88)
    except socket.error as e:
        Log.critical("[*] Server Socket occupation conflict")
        raise e
    Log.info("[*] Server %s://%s:%d started! fd=[%s]"
             %("https" if ssl_enable else "http",HOST,PORT,s.fileno()))
    return s


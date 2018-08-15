import socket

HOST = ''
PORT = 8000

def gen_serversock(port=None):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, port or PORT))
        s.listen(88)
    except socket.error as e:
        raise e
    return s


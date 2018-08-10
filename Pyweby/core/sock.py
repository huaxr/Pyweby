import socket

HOST = ''
PORT = 8000

def gen_serversock():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(128)
    except socket.error as e:
        raise e
    return s


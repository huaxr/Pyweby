#coding: utf-8
import socket
from compat.compat import B_DCRLF
from log.logger import init_loger, traceback

Log = init_loger(__name__)

def blocking_recv(self, sock, timeout=None):
    sock.settimeout(timeout or 1)
    data_ = []
    length = 0
    pos = 0
    while 1:
        try:
            data = sock.recv(65535)
        except (socket.error, socket.timeout, Exception) as e:
            Log.info(traceback(e))
            # self.close(sock)
            break  # turn continue to break. or will drop-dead halt

        if data.startswith(b'GET'):
            if data.endswith(B_DCRLF):
                data_.append(data)
                break
            else:
                data_.append(data)

        elif data.startswith(b'POST'):
            # TODO, blocking recv , how to solving.
            # server side uploading .
            sock.setblocking(1)
            length = int(self._re.findall(data)[0].decode())
            header_part, part_part = self.__re.split(data, 1)

            data_.extend([header_part, B_DCRLF, part_part])
            pos = len(part_part)
            self._POST = True

        elif data.startswith(b'PUT'):
            sock.setblocking(1)
            self._PUT = True

        elif data.startswith(b'DELETE'):
            sock.setblocking(1)
            self._DELETE = True

        elif data.startswith(b'OPTIONS'):
            sock.setblocking(1)
            self._OPTIONS = True

        elif data.startswith(b'HEAD'):
            sock.setblocking(1)
            self._HEAD = True

        if self._POST:
            if length <= pos:
                if data and not data.startswith(b'POST'):
                    # always put the last pieces of raw data in the list
                    # otherwise, the data will be incomplete and the file
                    # will fail.
                    # after this, break while, recv complete.
                    data_.append(data)
                break
            else:
                if data and not data.startswith(b'POST'):
                    data_.append(data)
                    pos += len(data)
    return b''.join(data_)
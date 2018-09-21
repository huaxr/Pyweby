from collections import namedtuple
import six
from abc import ABCMeta,abstractmethod
from urllib import request
HTTPCLIENT = request

@six.add_metaclass(ABCMeta)
class AsyncHTTPClient():
    observer = []

    @abstractmethod
    def add(self,observer):
        pass

    @abstractmethod
    def remove(self,observer):
        pass

    @abstractmethod
    def notify(self):
        pass


class Notify(AsyncHTTPClient):

    def add(self,observer):
        self.observer.append(observer)

    def remove(self,observer):
        self.observer.remove(observer)

    def notify(self):
        for ob in self.observer:
            ob.requests()

    def __iadd__(self, other):
        self.add(other)


@six.add_metaclass(ABCMeta)
class Observer():
    def __init__(self,ob):
        self.ob = ob

    def urlopen(self,observer):
        url = observer.url
        data = observer.data
        headers = observer.headers
        # if data is None, default is get method, else POST
        req = HTTPCLIENT.Request(url=url, data=data,headers=headers)
        res = HTTPCLIENT.urlopen(req)
        return res

    @abstractmethod
    def requests(self):
        pass

class ClientObserver(Observer):
    RES = []
    def requests(self):
        res = self.urlopen(self.ob)    # need call .read to read the content
        self.RES.append(res)


class NAMEDTUPLE(object):
    def __init__(self, url=None, data=None, headers=None):
        self.url = url
        self.data = data
        self.headers = headers
        self.namedtupel = namedtuple('xx', ['url', 'data', 'headers'])

    def __call__(self, *args, **kwargs):
        return self.namedtupel(url=self.url, data=self.data, headers=self.headers)




class AsyncClient(object):
    notify = Notify()

    def add_request(self, url=None, data=None, headers=None):
        '''
        call notify add to add an observer request in the
        notity's observer
        '''
        klaus = NAMEDTUPLE(url=url, data=data, headers=headers)()
        ob = ClientObserver(klaus)
        self.notify.add(ob)

    def request(self):
        self.notify.notify()

    @property
    def get_result(self):
        return self.notify.observer[0].RES


if __name__ == '__main__':
    a = AsyncClient()
    a.add_request('https://www.baidu.com',b'x',{})
    a.add_request('http://www.baidu.com', b'x', {})
    # x = a.request('http://www.baidu.com', b'x', {})
    # a.request()
    a.request()
    print(a.get_result[0].read())



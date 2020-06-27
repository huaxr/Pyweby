import sys
from collections import namedtuple
from compat.compat import REDUCE as reduce

class AuthHandler(object):
    def __init__(self,cls):
        self.cls = cls

    def __call__(self, *args, **kwargs):
        return self.cls


def login_require(obj):
    # get_handler = obj.__dict__.get('get',None)
    # post_handler = obj.__dict__.get('post',None)
    # if get_handler:
    #     '''
    #     setattr can change the class's attribute dynamic.
    #     '''
    #     setattr(obj, "get", AuthHandler(get_handler,obj))
    # if post_handler:
    #     setattr(obj, "post", AuthHandler(post_handler,obj))
    def check_cookie():
        return AuthHandler(obj)
    setattr(obj, '_'+sys._getframe(0).f_code.co_name, check_cookie)
    return obj


R = '0001' #READ(normal user)
W = '0010' #WRITE(change file or create file.)  can_write
U = '0100' #UPLOAD(uploading files)             can_upload
A = '1000' #ADMIN(with all privilege)           is_admin


def user_level(flag):
    if isinstance(flag,PRIVILIGE):
        flag = repr(flag)
    INT = int(flag,2)
    levels = []
    for i in range(0,4):
        levels.append(INT >> i & 1 or 0)
    tuples = namedtuple('NONE', ['can_read','can_write','can_upload','is_admin'])
    return tuples._make(levels)


class PRIVILIGE(object):
    R = '0001'  # READ(normal user)
    W = '0011'  # WRITE(change file or create file.)  can_write
    U = '0101'  # UPLOAD(uploading files)             can_upload
    A = '1001'  # ADMIN(with all privilege)           is_admin

    PRIV = {'R':R,'W':W,'U':U,'A':A}

    def __init__(self,flag):
        self.flag = flag

    def __contains__(self, item):
        return item in self.PRIV


    def __repr__(self):
        tmp = []
        for i in str(self.flag):
            tmp.append(self.PRIV.get(i,'0001'))

        t = []
        # flags = reduce(lambda x,y: int(x,2) & int(y,2), tmp)
        # return bin(flags)[2:]
        for i in tmp:
            t.append(int(i,2))

        flags = reduce(lambda x,y: x|y, t)

        return bin(flags)[2:].rjust(4,'0')


class Sessions(dict):
    def __init__(self):
        self.dict = {}
        super(Sessions,self).__init__()

    @property
    def session(self):
        return self.dict

    @session.setter
    def session(self,value):
        self.dict[self.__repr__()] = value

    @session.deleter
    def session(self):
        del self.dict[self.__repr__()]


class Session(dict):

    def __init__(self):
        self.dict = {}
        super(Session,self).__init__()

    def get_session(self,session):
        return self.dict.get(session,'')

    def set_session(self,session,value):
        self.dict[session] = value

    def del_session(self,session):
        del self.dict[session]

    def __setitem__(self, session, value):
        self.dict[session] = value

    def __getitem__(self, session):
        return self.dict[session]

    def __delitem__(self, session):
        del self.dict[session]

    def __iter__(self):
        return self.dict.items()

    def __repr__(self):
        return "Session with %d items" %len(self.dict)

    def __call__(self, *args, **kwargs):
        return self.dict.keys()


    @property
    def keys(self):
        return self.dict.keys()

    @property
    def values(self):
        return self.dict.values()

    def clear(self):
        self.dict.clear()

    def __contains__(self, item):
        return item in self.dict

    def __iadd__(self, other):
        self.update(other)
        return self

    def __add__(self, other): d = Session();d.update(other);return d

class _property(property):

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func
        super(_property,self).__init__()

    def __set__(self, obj, value):
        print("xxx",self,obj,value)
        obj.__dict__[self.__name__] = value


    def __get__(self, obj, type=None):

        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, 1)


        if value is 1:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

class xxx(object):

    @_property
    def xx(self):
        a = 1
        b = 2
        return a+b


# @_property
# def xx():
#     a = 1
#     b = 2
#     return a+b
a = xxx()
c = a.xx

print("zzz",a.__dict__)

# xx()
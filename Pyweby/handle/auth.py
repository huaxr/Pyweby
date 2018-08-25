import sys

class AuthHandler(object):
    def __init__(self,cls):
        self.cls = cls

    def __call__(self, *args, **kwargs):
        print(args)


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
    setattr(obj, sys._getframe(0).f_code.co_name, check_cookie)
    return obj

import functools
import types

from concurrent.futures import ThreadPoolExecutor
try:
    import asyncio
except ImportError:
    asyncio = None

if asyncio is not None:
    Future = asyncio.Future


class Executor(ThreadPoolExecutor):
    '''
    __all__ = (ThreadPoolExecutor,)

    def __getattr__(name):
        if name == 'ThreadPoolExecutor':
            from .thread import ThreadPoolExecutor as te
            ThreadPoolExecutor = te
            return te
    '''
    _instance_ = None

    def __new__(cls, *args, **kwargs):
        if not getattr(cls,'_instance', None):
            cls._instance = ThreadPoolExecutor(max_workers=10)
        return cls._instance


def asyncpool(*args, **kwargs):

    '''
    an descriptor use for concurrent programming.
    if method been wrapper by this function, it will
    execute on the executor object from concurrent.futures.ThreadPoolExecutor.

    that's means no blocking when executing an time-consumed code block.

    '''
    def run_on_executor_decorator(fn):

        exector_default = Executor()
        executor = kwargs.get("executor", exector_default)

        @functools.wraps(fn)
        def wrapper(self,*args, **kwargs):
            '''
            self is the router you defined which is subclass of HttpRequest,
            submit arguments detail.
            the first is the function or method to call
            the second if there is an class wrapper function, pass the call obj (self) to it

            >>> print(self,*args, **kwargs)
            >>  returns <class '__main__.testRouter'> (5,) {}
            '''
            future = executor.submit(fn,self, *args, **kwargs)

            '''
            call result() method from future object is blocking method.
            so , here we could't return this directly
            '''
            return future

        return wrapper
    return run_on_executor_decorator



import functools
from util._compat import COUNT
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor

import os

try:
    import asyncio
except ImportError:
    asyncio = None

if asyncio is not None:
    Future = asyncio.Future


class Executor(ThreadPoolExecutor):
    '''
    ThreadPoolExecutor attribute:

    example:
    def gcd(pair):
        a, b = pair
        low = min(a, b)
        for i in range(low, 0, -1):
            if a % i == 0 and b % i == 0:
                return i

    numbers = [
        (1963309, 2265973), (1879675, 2493670), (2030677, 3814172),
        (1551645, 2229620), (1988912, 4736670), (2198964, 7876293)
    ]


    - map:
    with ProcessPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(gcd, numbers))

    - submit
    with ProcessPoolExecutor(max_workers=2) as pool:
        for pair in numbers:
            future = pool.submit(gcd, pair)
    '''
    _instance_ = None

    def __new__(cls, *args, **kwargs):
        if not getattr(cls,'_instance', None):
            cls._instance = ThreadPoolExecutor(max_workers=(COUNT))
        return cls._instance


class Executorp(ProcessPoolExecutor):
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
            cls._instance = ProcessPoolExecutor(max_workers=COUNT)
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
        def wrapper(self, *args, **kwargs):
            '''
            self is the router you defined which is subclass of HttpRequest,
            submit arguments detail.
            the first is the function or method to call
            the second if there is an class wrapper function, pass the call obj (self) to it

            >>> print(self,*args, **kwargs)
            >>  returns <class '__main__.testRouter'> (5,) {}
            '''
            future = executor.submit(fn, self, *args, **kwargs)
            '''
            call result() method from future object is blocking method.
            so , here we could't return this directly
            '''
            return future

        return wrapper
    return run_on_executor_decorator



def safe_lock(func):
    """
    When concurrent applied . multiprocessing will raise expropriation
    condition . use this to avoiding the stuation
    """
    def lock(self, *args, **kwargs):
        if self.concurrent:
            with self._rlock:
                return func(self, *args, **kwargs)
        else:
            return func(self, *args, **kwargs)

    return lock


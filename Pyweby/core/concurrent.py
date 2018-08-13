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


def _create_future():
    future = Future()
    # Fixup asyncio debug info by removing extraneous stack entries
    source_traceback = getattr(future, "_source_traceback", ())
    while source_traceback:
        # Each traceback entry is equivalent to a
        # (filename, self.lineno, self.name, self.line) tuple
        filename = source_traceback[-1][0]
        if filename == __file__:
            del source_traceback[-1]
        else:
            break
    return future


def async_wait(func):
    wrapped = func
    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        future = _create_future()
        try:
            result = func(*args, **kwargs)
        except StopIteration:
            pass
        except Exception as e:
            raise e
        else:
            if isinstance(result, types.GeneratorType):
                yielded = next(result)
                runner = Runner(result, future, yielded)
                future.add_done_callback(lambda _: runner)
        return future
    return wrapper

class Runner(object):
    def __init__(self, gen, result_future, first_yielded):
        self.gen = gen
        self.result_future = result_future

    def run(self):
        """Starts or resumes the generator, running until it reaches a
        yield point that is not ready.
        """
        if self.running or self.finished:
            return
        try:
            self.running = True
            while True:
                future = self.future
                if not future.done():
                    return
                self.future = None
                try:
                    orig_stack_contexts = stack_context._state.contexts
                    exc_info = None

                    try:
                        value = future.result()
                    except Exception:
                        self.had_exception = True
                        exc_info = sys.exc_info()
                    future = None

                    if exc_info is not None:
                        try:
                            yielded = self.gen.throw(*exc_info)
                        finally:
                            # Break up a reference to itself
                            # for faster GC on CPython.
                            exc_info = None
                    else:
                        yielded = self.gen.send(value)

                    if stack_context._state.contexts is not orig_stack_contexts:
                        self.gen.throw(
                            stack_context.StackContextInconsistentError(
                                'stack_context inconsistency (probably caused '
                                'by yield within a "with StackContext" block)'))
                except (StopIteration, Return) as e:
                    self.finished = True
                    self.future = _null_future
                    if self.pending_callbacks and not self.had_exception:
                        # If we ran cleanly without waiting on all callbacks
                        # raise an error (really more of a warning).  If we
                        # had an exception then some callbacks may have been
                        # orphaned, so skip the check in that case.
                        raise LeakedCallbackError(
                            "finished without waiting for callbacks %r" %
                            self.pending_callbacks)
                    future_set_result_unless_cancelled(self.result_future,
                                                       _value_from_stopiteration(e))
                    self.result_future = None
                    self._deactivate_stack_context()
                    return
                except Exception:
                    self.finished = True
                    self.future = _null_future
                    future_set_exc_info(self.result_future, sys.exc_info())
                    self.result_future = None
                    self._deactivate_stack_context()
                    return
                if not self.handle_yield(yielded):
                    return
                yielded = None
        finally:
            self.running = False

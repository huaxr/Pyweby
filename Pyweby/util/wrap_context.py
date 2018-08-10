def wrap(fn):
    if fn is None or hasattr(fn, '_wrapped'):
        return fn
    def null_wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    null_wrapper._wrapped = True
    return null_wrapper

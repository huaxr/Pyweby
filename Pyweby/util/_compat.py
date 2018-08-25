import sys
import os
PY3 = sys.version_info >= (3,)

if hasattr(os,'cpu_count'):
    COUNT = (os.cpu_count() or 1) * 5
else:
    COUNT = 10

if PY3:
    STRING = (str,bytes)
else:
    STRING = (str, unicode,bytes)
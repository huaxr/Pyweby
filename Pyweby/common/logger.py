#coding=utf-8

import logging
import platform
import os
import sys

from common.exception import NoPackageFound
LOGGER = None


def traceback(msg,type=None):
    _name = os.path.basename(sys._getframe(1).f_code.co_filename)
    _func = sys._getframe(1).f_code.co_name
    line = str(sys._getframe(1).f_lineno)
    res =  ' |  '.join([str(msg),"file:"+_name,_func,"line:"+line])
    if type == 'error':
        return '[!] ' + res
    elif type == 'info':
        return '[*] ' + res
    else:
        return  '[-] ' + res

def set_level(level):
    global LOGGER
    LOGGER.setLevel(level)


def Logger(logger_name=None,log_file=None):
    global LOGGER
    if not LOGGER:
        init_config(logger_name,log_file)
    return LOGGER

def get_current_path():
    return os.path.dirname(os.path.realpath(__file__))


def get_file_handler(log_file):
    file_handler = logging.FileHandler(os.path.join(get_current_path(),log_file))
    file_formatter = logging.Formatter('[%(asctime)s] %(message)s')
    file_handler.setFormatter(file_formatter)
    return file_handler

def get_stream_handler():
    stream_handler = logging.StreamHandler()
    if platform.system() == 'Windows':
        stream_formatter = logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S")
        stream_handler.setFormatter(stream_formatter)
    else:
        try:
            from colorlog import ColoredFormatter
        except ImportError:
            raise NoPackageFound(pkname='colorlog')
        LOGFORMAT = "%(log_color)s[%(asctime)s]%(reset)s %(log_color)s[%(levelname)s] %(message)s%(reset)s"
        stream_formatter = ColoredFormatter(LOGFORMAT, "%H:%M:%S")
        stream_handler.setFormatter(stream_formatter)
    return stream_handler

def init_config(logger_name=None,log_file=None):
    global LOGGER
    LOGGER = logging.getLogger(logger_name)

    stream_handler = get_stream_handler()
    if log_file:
        file_handler = get_file_handler(log_file)
        LOGGER.addHandler(file_handler)

    LOGGER.addHandler(stream_handler)
    return LOGGER


def init_loger(name):
    Log = Logger(name)
    Log.setLevel(logging.INFO)
    return Log
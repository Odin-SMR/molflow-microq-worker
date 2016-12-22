import os
import logging
import logging.handlers
import sys

try:
    from cloghandler import (
        ConcurrentRotatingFileHandler as RotatingFileHandler)
except ImportError:
    RotatingFileHandler = logging.handlers.RotatingFileHandler

STD_FORMAT = '%(asctime)s - %(levelname)s: %(message)s'
STD_LOGPATH = '/home/logs'

LOGGERS = set()


def get_logger(name, to_file=True, to_stdout=False,
               log_path=STD_LOGPATH, format_str=STD_FORMAT):

    logger = logging.getLogger(name)

    if name in LOGGERS:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(format_str)

    if to_file:
        os.system('mkdir -p %s' % log_path)
        file_path = os.path.join(log_path, '%s.log' % name)
        handler = RotatingFileHandler(
            file_path, maxBytes=5e6, backupCount=5)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    if to_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    LOGGERS.add(name)
    return logger

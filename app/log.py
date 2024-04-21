import time

from loguru import logger
from termcolor import cprint

print_stdout = True


def log_exception(exception):
    logger.exception(exception)


def log_and_print(msg):
    logger.info(msg)
    if print_stdout:
        print(msg)


def log_and_cprint(msg, *args, **kwargs):
    logger.info(msg)
    if print_stdout:
        cprint(msg, *args, **kwargs)


def log_and_always_print(msg):
    """
    A mode which always print to stdout, no matter what.
    Useful when running multiple tasks and we just want to see the important information.
    """
    logger.info(msg)
    # always include time for important messages
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"\n[{t}] {msg}")


def print_with_time(msg):
    """
    Print a msg to console with timestamp.
    """
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"\n[{t}] {msg}")

import logging
import os
import time

from termcolor import cprint


print_stdout = True


def create_new_logger(task_id: str, out_dir: str):
    """
    Create a new logger with task_id as name, and store the file in out_dir.
    """
    logger = logging.getLogger(task_id)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    info_file_handler = logging.FileHandler(__info_file_name(out_dir))
    info_file_handler.setLevel(logging.INFO)
    info_formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
    info_file_handler.setFormatter(info_formatter)
    logger.addHandler(info_file_handler)
    return logger


def get_logger(task_id: str):
    """
    Retrieve an existing logger.
    """
    return logging.getLogger(task_id)


def log_exception(logger, error):
    logger.exception(error)


def log_and_print(logger, msg):
    logger.info(msg)
    if print_stdout:
        print(msg)


def log_and_cprint(logger, msg, *args, **kwargs):
    logger.info(msg)
    if print_stdout:
        cprint(msg, *args, **kwargs)


def log_and_always_print(logger, msg):
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


def __info_file_name(out_dir: str):
    """
    Helper method to get info logger name.
    """
    fname = "info.log"
    info_file = os.path.join(out_dir, fname)
    return info_file

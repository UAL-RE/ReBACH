__version__ = "1.0.0"

from functools import wraps
from enum import IntEnum
from logging import Logger
from typing import Callable


class Status(IntEnum):
    SUCCESS = 0
    ERROR = 1
    INVALID_PATH = 2
    DUPLICATE_BAG = 3
    INVALID_PACKAGE = 4
    WASABI_ERROR = 5
    INVALID_CONFIG = 6
    DRY_RUN = SUCCESS


# Adapted from https://github.com/haarcuba/dryable (MIT License)
# Copyright (c) 2019 Yoav Kleinberger
class Dryable:
    dry_run: bool = False
    log: Logger

    def __init__(self, *, dry_return=None):
        """
        Enable dry-run of a function.

        :param dry_return: Return this value when skipping the function.
        """
        self.dry_return = dry_return

    @classmethod
    def activate(cls, value: bool, log: Logger) -> None:
        if value:
            cls.dry_run = True
            cls.log = log
        else:
            cls.dry_run = False

    def __call__(self, function: Callable) -> Callable:
        @wraps(function)
        def _decorated(*args, **kwargs):
            if self.dry_run:
                args_string = ', '.join([str(argument) for argument in args])
                kwargs_string = ', '.join(
                    ['{}={}'.format(key, value) for (key, value) in kwargs.items()])
                if len(kwargs) > 0:
                    if len(args) > 0:
                        kwargs_string = ', {}'.format(kwargs_string)
                logging_msg = f'Skipped: {function.__qualname__}( {args_string}{kwargs_string} )'
                self.log.info(logging_msg)
                return self.dry_return
            return function(*args, **kwargs)

        return _decorated


activate = Dryable.activate

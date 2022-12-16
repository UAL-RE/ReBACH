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
    DRY_RUN = 7


# Adapted from https://github.com/haarcuba/dryable
class Dryable:
    _dryRun: bool
    _log: Logger

    def __init__(self, value=None):
        self._value = value

    @classmethod
    def activate(cls, value: bool, log: Logger) -> None:
        if value:
            cls._dryRun = True
            cls._log = log
        else:
            cls._dryRun = False

    def __call__(self, function: Callable) -> Callable:
        @wraps(function)
        def _decorated(*args, **kwargs):
            if self._dryRun:
                args_string = ', '.join([str(argument) for argument in args])
                kwargs_string = ', '.join(
                    ['{}={}'.format(key, value) for (key, value) in kwargs.items()])
                if len(kwargs) > 0:
                    if len(args) > 0:
                        kwargs_string = ', {}'.format(kwargs_string)
                logging_msg = f'Skipped: {function.__qualname__}( {args_string}{kwargs_string} )'
                self._log.info(logging_msg)
                return self._value
            return function(*args, **kwargs)

        return _decorated


activate = Dryable.activate

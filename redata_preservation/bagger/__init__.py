from enum import Enum


class Status(Enum):
    SUCCESS = 0
    ERROR = 1
    INVALID_PATH = 2
    DUPLICATE_BAG = 3
    INVALID_PACKAGE = 4
    WASABI_ERROR = 5

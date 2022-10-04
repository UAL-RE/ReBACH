import configparser

from .. import config_file

from .dict_load import dict_load

config_default_dict = dict_load(config_file)
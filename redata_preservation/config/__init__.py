import argparse
import configparser

from argparse import Namespace
from configparser import ConfigParser


def get_args() -> tuple[Namespace, ConfigParser]:
    """
    Construct args namespace from config file, overriding with values
    specified at runtime

    :return: Tuple of populated args namespace and config variable
    """
    conf_parser = argparse.ArgumentParser(
        description=__doc__,  # printed with -h/--help
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    conf_parser.add_argument('-c', '--config',
                             help='Path to configuration file.',
                             default='redata_preservation/config/default.ini')
    args, remaining_argv = conf_parser.parse_known_args()

    defaults = {
        # This puts the correct config file into the args object
        'config': args.config,
        'delete': True,
        'overwrite': False
    }

    config = configparser.ConfigParser()
    config.read([args.config])
    defaults.update(dict(config.items("Defaults")))

    parser = argparse.ArgumentParser(
        # Inherit options from conf_parser
        parents=[conf_parser]
    )
    parser.set_defaults(**defaults)
    parser.add_argument('-b', '--batch', help='Process a batch directory.')
    parser.add_argument('-d', '--delete', help='Delete bags after upload.',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('-o', '--output_dir',
                        help='Output directory for generated bags.')
    parser.add_argument('-w', '--workflow', help='Path to workflow file.')
    parser.add_argument('--dart_command', help='Command to invoke DART Runner.')
    parser.add_argument('--overwrite', help='Overwrite duplicate bags.',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('path', help='Path to the package or batch directory')
    args = parser.parse_args(remaining_argv)

    return args, config

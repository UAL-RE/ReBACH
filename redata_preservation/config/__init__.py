import argparse
import sys
from argparse import Namespace

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Override tomllib.TOMLDecodeError to include filename as a property
class TOMLDecodeError(tomllib.TOMLDecodeError):
    def __init__(self, message, filename):
        super().__init__(message)
        self.filename = filename


def get_args() -> tuple[Namespace, dict]:
    """
    Construct args namespace from config file, overriding with values
    specified at runtime

    :return: Tuple of populated args namespace and config variable
    """
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument('-c', '--config',
                             help='Path to configuration file.',
                             default='redata_preservation/config/default.ini')
    args, remaining_argv = conf_parser.parse_known_args()

    defaults = {  # This puts the correct config file into the args object
        'config': args.config, 'delete': True, 'overwrite': False}

    with open(args.config, "rb") as f:
        try:
            config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise TOMLDecodeError(e, filename=args.config)

    defaults.update(dict(config['Defaults']))

    parser = argparse.ArgumentParser(  # Inherit options from conf_parser
        parents=[conf_parser])
    parser.set_defaults(**defaults)
    parser.add_argument('-b', '--batch', help='Process a batch directory.')
    parser.add_argument('-d', '--delete', help='Delete bags after upload.',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('-o', '--output_dir',
                        help='Output directory for generated bags.')
    parser.add_argument('-w', '--workflow', help='Path to workflow file.')
    parser.add_argument('--dart_command',
                        help='Command to invoke DART Runner.')
    parser.add_argument('--overwrite', help='Overwrite duplicate bags.',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('path', help='Path to the package or batch directory')
    args = parser.parse_args(remaining_argv)

    return args, config

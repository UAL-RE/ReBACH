import argparse
import sys
from argparse import Namespace, BooleanOptionalAction
from os import PathLike
from pathlib import Path
from typing import Optional, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Override tomllib.TOMLDecodeError to include filename as a property
class TOMLDecodeError(tomllib.TOMLDecodeError):
    def __init__(self, message, filename):
        super().__init__(message)
        self.filename = filename


def get_args(path: Optional[PathLike] = None,
             default_conf: Optional[PathLike] = None) -> Union[dict, tuple[Namespace, dict]]:
    """
    Construct args namespace from config file, overriding with values
    specified at runtime

    :return: Tuple of populated args namespace and config variable
    """
    if not default_conf:
        default_conf = Path('bagger/config/default.toml')

    if path:
        with open(default_conf, "rb") as f:
            try:
                config = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                raise TOMLDecodeError(e, filename=default_conf)
        return config

    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument('-c', '--config', metavar='config_file',
                             help='Path to configuration file.',
                             default=default_conf)
    args, remaining_argv = conf_parser.parse_known_args()

    defaults = {  # This puts the correct config file into the args object
        'config': args.config, 'delete': True, 'overwrite': False, 'dry_run': False
    }

    with open(args.config, "rb") as f:
        try:
            config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise TOMLDecodeError(e, filename=args.config)

    defaults.update(dict(config['Defaults']))

    parser = argparse.ArgumentParser(  # Inherit options from conf_parser
        parents=[conf_parser])
    parser.set_defaults(**defaults)
    parser.add_argument('-b', '--batch', metavar='batch_dir',
                        help='Process a batch directory.')
    parser.add_argument('-d', '--delete',
                        help='Delete bags after upload.', action=BooleanOptionalAction)
    parser.add_argument('-o', '--archival_staging_storage', metavar='archival_staging_storage',
                        help='Output directory for generated bags.')
    parser.add_argument('-w', '--workflow', metavar='workflow_file',
                        help='Path to workflow file.')
    parser.add_argument('--dart_command', metavar='dart_command',
                        help='Command to invoke DART Runner.')
    parser.add_argument('--overwrite',
                        help='Overwrite duplicate bags.', action=BooleanOptionalAction)
    parser.add_argument('--dry-run', '--dryrun',
                        help='Log execution steps without actually executing. (default: False)',
                        action='store_true')
    parser.add_argument('path', help='Path to the package or batch directory.')
    args, remaining_argv = parser.parse_known_args(remaining_argv)

    return args, config

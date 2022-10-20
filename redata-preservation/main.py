#!/usr/bin/python3

import argparse
import configparser
import os
import sys

from job import Job

def get_args():
    """
    Construct args namespace from config file, overriding with values specified
    at runtime with args specified on the command line.

    :return: Tuple of populated args namespace and config variable
    """

    conf_parser = argparse.ArgumentParser(
        description=__doc__,  # printed with -h/--help
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    conf_parser.add_argument('-c', '--config',
                             help='Path to configuration file.',
                             default='config/default.ini')
    args, remaining_argv = conf_parser.parse_known_args()

    defaults = {
        'delete':'True',
        'output_dir':'../out',
        'workflow':'config/default_workflow.json'
    }

    config = configparser.ConfigParser()
    config.read([args.config])
    defaults.update(dict(config.items("Defaults")))

    parser = argparse.ArgumentParser(
        # Inherit options from config_parser
        parents=[conf_parser]
    )
    parser.set_defaults(**defaults)
    parser.add_argument('-b', '--batch', help='Process a batch directory.')
    parser.add_argument('-d', '--delete', help='Delete bags after upload.')
    parser.add_argument('-o', '--output_dir',
                             help="Output directory for bags.")
    parser.add_argument('-w', '--workflow', help="Path to workflow file.")
    parser.add_argument('path')
    args = parser.parse_args(remaining_argv)

    return args,config

def run_dart(path, bag_title, workflow, output_dir, delete, dart_command):
    """
    Run DART executable for a single package

    :param path: Path of preservation package
    :param bag_title: Title for bag
    :param workflow: Path to workflow JSON file
    :param output_dir: Directory for generated bag output by DART
    :param delete: Delete output bag if true
    :param dart_command: Path to DART executable

    :return: Exit code from DART executable
    """

    package_name = path + '.tar'

    job = Job(workflow, package_name, output_dir, delete, dart_command)

    job.add_file(path)

    job.add_tag("bag-info.txt", "Source-Organization", "ReDATA")
    job.add_tag("aptrust-info.txt", "Access", "Institution")
    job.add_tag("aptrust-info.txt", "Title", bag_title)

    exit_code = job.run()

    return exit_code

def run_batch(batch_path: str, **kwargs):
    """
    Run DART executable on a batch of packages.
    :param batch_path: Path to batch folder containing packages
    :param kwargs: Remainder of arguments passed to run_dart()
    """
    for path in next(os.walk(batch_path))[1]:
        run_dart(os.path.join(batch_path, path), **kwargs)

def main():
    args, config = get_args()

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['login']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['password']

    if args.batch:
        run_batch(
            args.path,
            bag_title="Bag " + args.path,
            workflow=args.workflow,
            output_dir=args.output_dir,
            delete=args.delete,
            dart_command=os.path.join(
                os.getcwd(),
                'dart-runner'
            )
        )

    else:
        run_dart(
            args.path,
            bag_title="Bag " + args.path,
            workflow=args.workflow,
            output_dir=args.output_dir,
            delete=args.delete,
            dart_command=os.path.join(
                os.getcwd(),
                'dart-runner'
            )
        )

if __name__ == '__main__':
    sys.exit(main())

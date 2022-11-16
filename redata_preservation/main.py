import json
import os
from configparser import ConfigParser
from enum import Enum
from logging import Logger
from os.path import dirname

from redata.commons import logger, git_info

from config import get_args
from job import Job
from metadata import get_metadata
from wasabi import Wasabi, get_filenames_from_ls


class Status(Enum):
    SUCCESS = 0
    ERROR = 1
    INVALID_PATH = 2
    DUPLICATE_BAG = 3
    INVALID_PACKAGE = 4


class Bagger:

    def __init__(self, workflow: str, output_dir: str, delete: bool,
                 dart_command: str, config: ConfigParser, log: Logger) -> None:
        """
        Set up environment for generating bags with DART

        :param workflow: Path to workflow JSON file
        :param output_dir: Directory for generated bag output by DART
        :param delete: Delete output bag if True
        :param dart_command: Path to DART executable
        :param config: ConfigParser object
        :param log: Logger object
        """
        self.config: ConfigParser = config
        self.log: Logger = log
        self.dart_command: str = dart_command
        self.delete: bool = delete
        self.output_dir: str = output_dir
        self.workflow: str = workflow

    @staticmethod
    def get_bag_name(package_path: str) -> str:  # Probably static
        """
        Get name for bag from package path, stripping subdirectories and slashes

        :param package_path: Path to package
        :return: Name for bag tarball
        """

        return os.path.basename(os.path.normpath(package_path)) + '.tar'

    def check_duplicate(self, bag_name: str) -> bool:
        """
        Check if package being processed has already been bagged and uploaded

        :param bag_name: Name for bag being processed
        :return: True if bag exists in storage, otherwise False
        """
        wasabi = Wasabi(access_key=self.config['Wasabi']['access_key'],
                        secret_key=self.config['Wasabi']['secret_key'],
                        s3host=self.config['Wasabi']['host'],
                        s3hostbucket=self.config['Wasabi']['host_bucket'],
                        log=self.log
                        )

        folder_to_list = f"s3://{self.config['Wasabi']['bucket']}"
        wasabi_files = wasabi.list_bucket(folder_to_list)
        filenames = get_filenames_from_ls(wasabi_files)

        return bag_name in filenames

    def run_dart(self, package_path: str) -> Status:
        """
        Run DART executable for a single package

        :param package_path: Path to preservation package
        :return: Status after attempting execution
        """
        if not os.path.exists(package_path):
            return Status.INVALID_PATH

        bag_name = self.get_bag_name(package_path)

        if self.check_duplicate(bag_name):
            return Status.DUPLICATE_BAG

        metadata = get_metadata(package_path)

        job = Job(self.workflow, bag_name, self.output_dir, self.delete,
                  self.dart_command)

        job.add_file(package_path)

        job.add_tag("bag-info.txt", "Source-Organization", "ReDATA")
        job.add_tag("aptrust-info.txt", "Access", "Institution")
        job.add_tag("aptrust-info.txt", "Title", metadata['title'])

        data, err, exit_code = job.run()

        # TODO: What if not data?
        if data:
            data = json.loads(data)

            errors = data['packageResult']['errors']
            errors |= data['validationResult']['errors']
            errors |= data['uploadResults'][0]['errors']

            if errors:
                log.warning(errors)
            else:
                log.info(f'Job succeeded: {bag_name}')

        return Status.SUCCESS


if __name__ == '__main__':
    args, config = get_args()

    library_root_path = dirname(dirname(__file__))
    gi = git_info.GitInfo(library_root_path)

    log_dir = config['Logging']['log_dir']
    logfile_prefix = config['Logging']['logfile_prefix']

    log = logger.log_setup(log_dir, logfile_prefix)

    lc = logger.LogCommons(log, 'script_run', gi)

    lc.script_start()
    lc.script_sys_info()

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

    bagger = Bagger(workflow=args.workflow, output_dir=args.output_dir,
                    delete=args.delete, dart_command='dart-runner',
                    config=config, log=log)

    if args.batch:
        log.info('Batch mode')
        log.info(f'  Batch path: {args.path}')
        for path in next(os.walk(args.path))[1]:
            bagger.run_dart(os.path.join(args.path, path))

    else:
        status = bagger.run_dart(args.path)
        log.info(f'Status: {status.name}')
        log.info(f'Exit code: {status.value}')

    lc.script_end()
    lc.log_permission()

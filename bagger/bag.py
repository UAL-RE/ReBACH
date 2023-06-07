import json
from logging import Logger
from os import PathLike
from pathlib import Path
from typing import Union

from bagger import Status, Dryable
from bagger.job import Job
from bagger.metadata import Metadata
from bagger.wasabi import Wasabi, get_filenames_from_ls
from bagger.ntf import NamedTemporaryFile, TemporaryFile


# TODO: Create BaggerInit class to initialize the Bagger environment. Bagger
#  class can then take the package_path and other arguments to enable looping.
class Bagger:

    def __init__(self, workflow: PathLike, output_dir: PathLike, delete: bool,
                 dart_command: str, config: dict, log: Logger,
                 overwrite: bool, dryrun: bool = False) -> None:
        """
        Set up environment for generating bags with DART

        :param workflow: Path to workflow JSON file
        :param output_dir: Directory for generated bag output by DART
        :param delete: Delete output bag if True
        :param dart_command: Path to DART executable
        :param config: Config dict
        :param log: Logger object
        :param overwrite: Overwrite duplicate bags if True
        """
        self.config: dict = config
        self.log: Logger = log
        self.dart_command: str = dart_command
        self.delete: bool = delete
        self.output_dir: PathLike = output_dir
        self.workflow: PathLike = workflow
        self.workflow_file: TemporaryFile = None
        self.overwrite: bool = overwrite
        self.dryrun: bool = dryrun

        if self.dryrun:
            self.log.info('DRYRUN MODE')
            Dryable.activate(True, self.log)

        self.wasabi = Wasabi(access_key=config['Wasabi']['access_key'],
                             secret_key=config['Wasabi']['secret_key'],
                             s3host=config['Wasabi']['host'],
                             s3bucket=config['Wasabi']['bucket'],
                             s3hostbucket=config['Wasabi']['host_bucket'],
                             dart_hostbucket_override=config['Wasabi']['dart_workflow_hostbucket_override'])

    @staticmethod
    def decompose_name(package_name: str) -> tuple[str, str, str]:
        """
        Decompose the name of a package into parts to enable traversing the
        package

        :param package_name: Name (directory) of package
        :return: Tuple of package name parts
        """
        # Format of preservation package name:
        # [article_id]_[version]_[first_depositor_full_name]_[metadata_hash]

        path_elements = package_name.split('_')

        # Article ID and version are the first and second elements
        article_id = path_elements[0]
        version = path_elements[1]
        # Depositor can be arbitrary number of elements because it is
        # snake-cased, so get hash as last element
        metadata_hash = path_elements[-1]

        return article_id, version, metadata_hash

    @staticmethod
    def validate_package(metadata_path: PathLike) -> bool:
        """
        Check if the package has a valid directory structure
        FIXME: The method currently only checks for the presence of the package
            metadata JSON file in the expected location. Eventually this should
            validate the entire package against the package structure schema.

        :param metadata_path: Path to preservation package metadata JSON file
        :return: True if the package is valid, otherwise False
        """

        return Path(metadata_path).exists()

    def _init_dart(self, package_path: PathLike) -> Union[Status, tuple[str, list]]:
        """
        Perform initial error checks and return data for DART data structure.
        Also overrides the workflow file host and bucket if the dart_hostbucket_override
        flag is set in the configuration file.

        :param package_path: Path to preservation package
        :return: Status if errors are encountered, otherwise bag name and tags
        """

        package_name = Path(package_path).name
        bag_name = f'{package_name}.tar'

        article_id, version, metadata_hash = self.decompose_name(package_name)
        metadata_dir = f'{version}/METADATA/'
        metadata_filename = f'{article_id}.json'
        metadata_path = Path(package_path, metadata_dir, metadata_filename)

        if not metadata_path.exists():
            return Status.INVALID_PATH

        folder_to_list = f"s3://{self.wasabi.s3bucket}"
        wasabi_ls, wasabi_error = self.wasabi.list_bucket(folder_to_list)

        if wasabi_error:
            wasabi_errors = (e for e in wasabi_error.split('\n') if e != '')
            for e in wasabi_errors:
                self.log.error(f"[Wasabi] {e.strip('ERROR: ')}")
            return Status.WASABI_ERROR

        wasabi_list = get_filenames_from_ls(wasabi_ls)

        if bag_name in wasabi_list and not self.overwrite:
            return Status.DUPLICATE_BAG

        if not self.validate_package(metadata_path):
            return Status.INVALID_PACKAGE

        metadata_tags = Metadata(self.config, metadata_path,
                                 self.log).parse_metadata()

        if not metadata_tags:
            return Status.INVALID_CONFIG

        if self.wasabi.dart_hostbucket_override:
            with open(self.workflow, 'r') as f:
                wkfl_json = json.load(f)
                if 'storageServices' not in wkfl_json:
                    print('storageServices key not found in DART workflow file')
                    return Status.INVALID_CONFIG
                for item in wkfl_json['storageServices']:
                    item['host'] = self.wasabi.s3host
                    item['bucket'] = self.wasabi.s3bucket
                    self.workflow_file = NamedTemporaryFile(prefix="rebach", mode="w", delete=True)
                    self.workflow_file.write(json.dumps(wkfl_json))
                    self.workflow_file.flush()
            self.workflow = self.workflow_file.name

        return bag_name, metadata_tags

    def run_dart(self, package_path: PathLike) -> Status:
        """
        Run DART executable for a single package

        :param package_path: Path to preservation package
        :return: Status after attempting execution
        """

        init_status = self._init_dart(package_path)
        if isinstance(init_status, Status):
            return init_status
        else:
            bag_name, metadata_tags = init_status

        job = Job(self.workflow, bag_name, self.output_dir, self.delete,
                  self.dart_command, self.log)

        job.add_file(package_path)

        for tag in metadata_tags:
            tag_file, tag_name, tag_value = tag
            job.add_tag(tag_file, tag_name, tag_value)

        data, error, exit_code = job.run()

        if error:
            # Remove trailing newline from DART runner error output
            self.log.error(error.rstrip())

        # TODO: What if not data?
        if data:
            data_json = json.loads(data)

            errors = data_json['packageResult']['errors']
            errors |= data_json['validationResult']['errors']
            errors |= data_json['uploadResults'][0]['errors']

            if errors:
                self.log.warning(errors)
            else:
                self.log.info(f'Job succeeded: {bag_name}')

        return Status(exit_code)

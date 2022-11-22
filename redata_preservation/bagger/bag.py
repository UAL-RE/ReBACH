import json
from configparser import ConfigParser
from logging import Logger
from os import path

from redata_preservation.bagger import Status
from redata_preservation.bagger.job import Job
from redata_preservation.bagger.metadata import get_metadata
from redata_preservation.bagger.wasabi import Wasabi, get_filenames_from_ls


class Bagger:

    def __init__(self, workflow: str, output_dir: str, delete: bool,
                 dart_command: str, config: ConfigParser, log: Logger,
                 overwrite: bool) -> None:
        """
        Set up environment for generating bags with DART

        :param workflow: Path to workflow JSON file
        :param output_dir: Directory for generated bag output by DART
        :param delete: Delete output bag if True
        :param dart_command: Path to DART executable
        :param config: ConfigParser object
        :param log: Logger object
        :param overwrite: Overwrite duplicate bags if True
        """
        self.config: ConfigParser = config
        self.log: Logger = log
        self.dart_command: str = dart_command
        self.delete: bool = delete
        self.output_dir: str = output_dir
        self.workflow: str = workflow
        self.overwrite: bool = overwrite

        self.wasabi = Wasabi(access_key=config['Wasabi']['access_key'],
                             secret_key=config['Wasabi']['secret_key'],
                             s3host=config['Wasabi']['host'],
                             s3hostbucket=config['Wasabi']['host_bucket'])

    @staticmethod
    def decompose_name(package_name: str) -> tuple[str, str, str]:
        """
        Decompose the name of a package into parts to enable parsing the package

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

    def list_wasabi(self) -> tuple[str, str]:
        """
        Check if package being processed has already been bagged and uploaded

        :return: True if bag exists in storage, otherwise False
        """
        folder_to_list = f"s3://{self.config['Wasabi']['bucket']}"
        return self.wasabi.list_bucket(folder_to_list)

    @staticmethod
    def validate_package(metadata_path: str) -> bool:
        """
        Check if the package has a valid directory structure
        FIXME: The method currently only checks for the presence of the package
            metadata JSON file in the expected location. Eventually this should
            validate the entire package against the package structure schema.

        :param metadata_path: Path to preservation package metadata JSON file
        :return: True if the package is valid, otherwise False
        """

        return path.exists(metadata_path)

    def run_dart(self, package_path: str) -> Status:
        """
        Run DART executable for a single package

        :param package_path: Path to preservation package
        :return: Status after attempting execution
        """

        # Get name for bag from package path, stripping subdirectories and
        # slashes
        bag_name = path.basename(path.normpath(package_path)) + '.tar'
        package_name = path.basename(path.normpath(package_path))

        article_id, version, metadata_hash = self.decompose_name(package_name)
        metadata_dir = f'v{version}/METADATA/'
        metadata_filename = f'preservation_final_{article_id}.json'
        metadata_path = path.join(package_path, metadata_dir, metadata_filename)

        if not path.exists(package_path):
            return Status.INVALID_PATH

        wasabi_ls, wasabi_error = self.list_wasabi()

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

        metadata = get_metadata(metadata_path)

        self.log.debug(metadata)

        job = Job(self.workflow, bag_name, self.output_dir, self.delete,
                  self.dart_command)

        job.add_file(package_path)

        job.add_tag("bag-info.txt", "Source-Organization", "ReDATA")
        job.add_tag("aptrust-info.txt", "Access", "Institution")
        job.add_tag("aptrust-info.txt", "Title", metadata['title'])

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

import json
from logging import Logger
from os import PathLike
from pathlib import Path
from shutil import rmtree
from typing import Union

from figshare.Utils import extract_item_id_only, extract_version_only, extract_metadata_hash_only, check_local_path, compare_hash
from figshare.Utils import extract_lastname_only, extract_bag_count, extract_bag_date, upload_to_remote, get_preserved_version_hash_and_size
from bagger import Status, Dryable
from bagger.job import Job
from bagger.metadata import Metadata
from bagger.wasabi import Wasabi, get_filenames_from_ls
from bagger.ntf import NamedTemporaryFile, TemporaryFile


# TODO: Create BaggerInit class to initialize the Bagger environment. Bagger
#  class can then take the package_path and other arguments to enable looping.
class Bagger:

    def __init__(self, workflow: PathLike, archival_staging_storage: PathLike, delete: bool,
                 dart_command: str, config: dict, log: Logger,
                 overwrite: bool, dryrun: bool = False) -> None:
        """
        Set up environment for generating bags with DART

        :param workflow: Path to workflow JSON file
        :param archival_staging_storage: Directory for generated bag output by DART if no upload
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
        self.archival_staging_storage: PathLike = archival_staging_storage
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
    def decompose_name(package_name: str) -> tuple[str, str, str, str, str, str]:
        """
        Decompose the name of a package into parts to enable traversing the
        package

        :param package_name: Name (directory) of package
        :return: Tuple of package name parts
        """
        # Format of preservation package name:
        # [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
        # bag_name_prefix is set in configuration.

        article_id = extract_item_id_only(package_name)
        version = extract_version_only(package_name)
        metadata_hash = extract_metadata_hash_only(package_name)
        last_name = extract_lastname_only(package_name)
        bag_count = extract_bag_count(package_name)
        bag_date = extract_bag_date(package_name)

        return article_id, version, metadata_hash, last_name, bag_count, bag_date

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

        article_id, version, metadata_hash, last_name, bag_count, bag_date = self.decompose_name(package_name)
        metadata_dir = f'{version}/METADATA/'
        metadata_filename = f'{article_id}.json'
        metadata_path = Path(package_path, metadata_dir, metadata_filename)

        if not metadata_path.exists():
            return Status.INVALID_PATH

        if upload_to_remote():
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
        else:
            version_local_final_preserved_list = check_local_path(int(article_id), version)
            version_final_storage_preserved_list = get_preserved_version_hash_and_size(int(article_id), version)
            if compare_hash(metadata_hash, version_local_final_preserved_list) or compare_hash(metadata_hash, version_final_storage_preserved_list):
                return Status.DUPLICATE_BAG

        if not self.validate_package(metadata_path):
            return Status.INVALID_PACKAGE

        metadata_tags = Metadata(self.config, metadata_path, article_id, version, last_name, metadata_hash, bag_count,
                                 self.log).parse_metadata()

        if not metadata_tags:
            return Status.INVALID_CONFIG

        with open(self.workflow, 'r') as f:
            wkfl_json = json.load(f)
            if 'storageServices' in wkfl_json:
                if self.wasabi.dart_hostbucket_override:
                    self.workflow_file = NamedTemporaryFile(prefix="rebach", mode="w", delete=True)
                    for item in wkfl_json['storageServices']:
                        if item:
                            item['host'] = self.wasabi.s3host
                            item['bucket'] = self.wasabi.s3bucket
                        else:
                            self.log.warning('item in storageServices key in DART workflow file is not valid. Bag upload disabled.')
                    self.workflow_file.write(json.dumps(wkfl_json))
                    self.workflow_file.flush()
                    self.workflow = self.workflow_file.name
            else:
                self.log.warning('storageServices key not found in DART workflow file. Bag upload disabled.')

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

        job = Job(self.workflow, bag_name, self.archival_staging_storage, self.delete,
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

            package_artifact = data_json['packageResult']['filepath'].replace('.tar', '_artifacts')
            package_artifact = Path(package_artifact)
            if package_artifact.exists() and package_artifact.is_dir():
                rmtree(package_artifact)

            errors = data_json['packageResult']['errors']
            errors |= data_json['validationResult']['errors']
            if len(data_json['uploadResults']) > 0:
                errors |= data_json['uploadResults'][0]['errors']

            if errors:
                self.log.warning(errors)
            else:
                self.log.info(f'Job succeeded: {bag_name}')

        return Status(exit_code)

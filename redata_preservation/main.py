import json
import os
import sys

from config import get_args
from job import Job
from metadata import get_metadata
from wasabi import Wasabi, get_filenames_from_ls


def check_duplicate(bag_name: str) -> bool:
    """
    Check if package being processed has already been bagged and uploaded
    :param bag_name: Name for bag being processed
    :return: True if bag exists in storage, otherwise False
    """
    w = Wasabi(access_key=config['Wasabi']['access_key'],
               secret_key=config['Wasabi']['secret_key'],
               s3host=config['Wasabi']['host'],
               s3hostbucket='%(bucket)s.s3.wasabisys.com'
               )

    folder_to_list = 's3://redata-preservation-test'
    wasabi_files = w.list_bucket(folder_to_list)
    filenames = get_filenames_from_ls(wasabi_files)

    return bag_name in filenames


def get_bag_name(bag_path: str) -> str:
    """
    Get name for bag from package path, stripping subdirectories and slashes
    :param bag_path: Path to package
    :return: Name for bag tarball
    """
    return os.path.basename(os.path.normpath(bag_path)) + '.tar'


def run_dart(package_path: str, workflow: str,
             output_dir: str, delete: bool, dart_command: str) -> int:
    """
    Run DART executable for a single package
    :param package_path: Path of preservation package
    :param workflow: Path to workflow JSON file
    :param output_dir: Directory for generated bag output by DART
    :param delete: Delete output bag if True
    :param dart_command: Path to DART executable

    :return: Exit code from DART executable
    """
    if not os.path.exists(package_path):
        sys.exit(f"Invalid path: {package_path}")

    bag_name = get_bag_name(package_path)

    if check_duplicate(bag_name):
        sys.exit(f"Duplicate bag: {bag_name}")

    metadata = get_metadata(package_path)

    job = Job(workflow, bag_name, output_dir, delete, dart_command)

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
            print(errors)
        else:
            print('Job succeeded')

        return exit_code


def run_batch(batch_path: str, **kwargs):
    """
    Run DART executable on a batch of packages.
    :param batch_path: Path to batch folder containing packages
    :param kwargs: Remainder of arguments passed to run_dart()
    """
    for path in next(os.walk(batch_path))[1]:
        run_dart(os.path.join(batch_path, path), **kwargs)


if __name__ == '__main__':
    args, config = get_args()
    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

    if args.batch:
        run_batch(
            batch_path=args.path,
            bag_title="Bag " + args.path,
            workflow=args.workflow,
            output_dir=args.output_dir,
            delete=args.delete,
            dart_command='dart-runner'
        )

    else:
        run_dart(
            package_path=args.path,
            workflow=args.workflow,
            output_dir=args.output_dir,
            delete=args.delete,
            dart_command='dart-runner'
        )

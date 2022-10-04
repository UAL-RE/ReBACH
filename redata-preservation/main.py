import os
import argparse
import configparser
from job import Job

def run_dart(path: str,
             bag_title: str,
             workflow: str,
             output_dir: str,
             delete: str,
             dart_command: str
             ):
    package_name = path + '.tar'

    job = Job(workflow, package_name, output_dir, delete, dart_command)

    job.add_file(path)

    job.add_tag("bag-info.txt", "Source-Organization", "ReDATA")
    job.add_tag("aptrust-info.txt", "Access", "Institution")
    job.add_tag("aptrust-info.txt", "Title", bag_title)

    exit_code = job.run()

    if exit_code == 0:
        print("Job completed")
    else:
        print("Job failed. Check the DART log for details.")

def run_batch(batch_path: str,
             bag_title: str,
             workflow: str,
             output_dir: str,
             delete: str,
             dart_command: str
             ):
    for path in next(os.walk(batch_path))[1]:
        run_dart(os.path.join(batch_path, path), bag_title, workflow, output_dir, delete, dart_command)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command-line interface for ReDATA Preservation workflow.')
    parser.add_argument('--config', required=True, help='Path to configuration file.')
    parser.add_argument('--batch', help='Process a batch directory instead of a single package.', default=True)
    parser.add_argument('--workflow', help="Path to workflow file.")
    parser.add_argument('--output_dir', help="Output directory for bags.")
    parser.add_argument('--delete', help='Delete bags after upload.')
    parser.add_argument('path')
    args = parser.parse_args()
    print(args)

    config = configparser.ConfigParser()
    config.read(args.config)

    # Setup environment

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['login']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['password']

    # Dart-runner only accepts env variables for 'login' and 'password'
    #os.environ['WASABI_HOST'] = config['Wasabi']['host']


    if args.batch:
        run_batch(
            args.path,
            "Bag " + args.path,
            args.workflow,
            args.output_dir,
            args.delete,
            os.path.join(os.getcwd(), 'redata-preservation', 'dart-runner')
        )
    else:
        run_dart(
            args.path,
            "Bag " + args.path,
            args.workflow,
            args.output_dir,
            args.delete,
            os.path.join(os.getcwd(), 'dart-runner')
        )




import os
import sys
from pathlib import Path
from redata.commons import logger

from bagger.bag import Bagger, Status
from bagger.config import get_args, TOMLDecodeError


def main() -> None:
    path = 'TestBags/7873476_01_Jeffrey_C_Oliver_b3e8ca9fce68c6dd95c4b71efe9220b7'
    init_log = logger.log_stdout()
    library_root_path = Path(__file__).resolve().parents[2]

    try:
        config = get_args(path=path)
    except TOMLDecodeError as e:
        init_log.error(f"Error in configuration file: {e.filename}")
        init_log.error(f"  TOML Decode Error: {e}")
        sys.exit(Status.INVALID_CONFIG)

    log_dir = config['Logging']['log_dir']
    logfile_prefix = config['Logging']['logfile_prefix']

    log = logger.log_setup(log_dir, logfile_prefix)

    log.info(f'Library root path: {library_root_path}')
    log.info(f'Config file: {config}')

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

    bagger = Bagger(workflow=config['Defaults']['workflow'],
                    output_dir=config['Defaults']['output_dir'],
                    delete=True,
                    dart_command=config['Defaults']['dart_command'],
                    config=config,
                    log=log,
                    overwrite=False)

    status = bagger.run_dart(path)
    log.info(f'Status: {status.name}')
    log.info(f'Exit code: {status}')

    sys.exit(status)


if __name__ == '__main__':
    main()

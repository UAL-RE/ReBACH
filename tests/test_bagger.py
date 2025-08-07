import os
import sys
from pathlib import Path

from redata.commons import logger

from bagger import Status
from bagger.bag import Bagger
from bagger.config import get_args, TOMLDecodeError

p = 'azu_1234567-v01-authorLastName-6de0ea5d4b2317d016c6db397bbebe86_bag_20250709'


def test_decompose_name():
    name_parts = Bagger.decompose_name(p)

    assert isinstance(name_parts, tuple)

    assert name_parts[0] == '1234567'
    assert name_parts[1] == 'v01'
    assert name_parts[2] == '6de0ea5d4b2317d016c6db397bbebe86'


def test_validate_package():
    pass


def test_run_dart(capsys):

    path = Path('tests', 'testbag', p)

    try:
        config = get_args(path=path)
    except TOMLDecodeError:
        sys.exit(Status.INVALID_CONFIG)

    log_dir = config['Logging']['log_dir']
    logfile_prefix = config['Logging']['logfile_prefix']

    log = logger.log_setup(log_dir, logfile_prefix)

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

    bagger = Bagger(workflow=Path('bagger/config/wasabi_test_workflow.json'),
                    archival_staging_storage=config['Defaults']['archival_staging_storage'],
                    delete=True,
                    dart_command=config['Defaults']['dart_command'],
                    config=config,
                    log=log,
                    overwrite=True)

    status = bagger.run_dart(path)

    assert status == 0


def test_batch():
    pass

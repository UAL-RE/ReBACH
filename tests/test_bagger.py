import sys

import pytest

from redata_preservation.bagger.bag import Bagger
from redata_preservation.scripts.main import main

p = '7873476_02_Jeffrey_C_Oliver_846ccf901fffd449e2d276285d15dca4'


def test_decompose_name():
    name_parts = Bagger.decompose_name(p)

    assert isinstance(name_parts, tuple)

    assert name_parts[0] == '7873476'
    assert name_parts[1] == '02'
    assert name_parts[2] == '846ccf901fffd449e2d276285d15dca4'


def test_validate_package():
    pass


def test_run_dart(capsys):
    with pytest.raises(SystemExit) as excinfo:
        args = ['-c=redata_preservation/config/arizona/arizona.ini',
                '-o=out',
                '-w=redata_preservation/config/redata-wasabi.json',
                f'TestBags/{p}/'
                ]
        sys.argv.extend(args)
        main()
    assert excinfo.value.code == 3


def test_batch():
    pass

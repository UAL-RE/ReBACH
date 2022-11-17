from redata_preservation.bagger.bag import Bagger


def test_decompose_name():
    p_name = '7873476_02_Jeffrey_C_Oliver_846ccf901fffd449e2d276285d15dca4'

    name_parts = Bagger.decompose_name(p_name)

    assert isinstance(name_parts, tuple)

    assert name_parts[0] == '7873476'
    assert name_parts[1] == '02'
    assert name_parts[2] == '846ccf901fffd449e2d276285d15dca4'

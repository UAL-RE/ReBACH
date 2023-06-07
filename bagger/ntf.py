import os, tempfile, gc


class TemporaryFile:
    """
    Creates a temporary file that allows opening a second time on Windows (use mode=None)
    https://gist.github.com/earonesty/a052ce176e99d5a659472d0dab6ea361
    https://stackoverflow.com/a/58956076
    https://stackoverflow.com/questions/23212435/permission-denied-to-write-to-my-temporary-file
    """
    def __init__(self, name, io, delete):
        self.name = name
        self.__io = io
        self.__delete = delete

    def __getattr__(self, k):
        return getattr(self.__io, k)

    def __del__(self):
        if self.__delete:
            try:
                self.__io.close()
                os.unlink(self.name)
            except FileNotFoundError:
                pass
            except PermissionError:
                print(f'Could not delete {self.name}. Permission denied or the file is being used by another process')


def NamedTemporaryFile(mode='w+b', bufsize=-1, suffix='', prefix='tmp', dir=None, delete=True):
    if not dir:
        dir = tempfile.gettempdir()
    name = os.path.join(dir, prefix + os.urandom(32).hex() + suffix)
    if mode is None:
        return TemporaryFile(name, None, delete)
    fh = open(name, "w+b", bufsize)
    if mode != "w+b":
        fh.close()
        fh = open(name, mode)
    return TemporaryFile(name, fh, delete)


def test_ntf_txt():
    x = NamedTemporaryFile("w")
    x.write("hello")
    x.close()
    assert os.path.exists(x.name)
    with open(x.name) as f:
        assert f.read() == "hello"


def test_ntf_name():
    x = NamedTemporaryFile(suffix="s", prefix="p")
    assert os.path.basename(x.name)[0] == 'p'
    assert os.path.basename(x.name)[-1] == 's'
    x.write(b"hello")
    x.seek(0)
    assert x.read() == b"hello"


def test_ntf_del():
    x = NamedTemporaryFile(suffix="s", prefix="p")
    assert os.path.exists(x.name)
    name = x.name
    del x
    gc.collect()
    assert not os.path.exists(name)


def test_ntf_mode_none():
    x = NamedTemporaryFile(suffix="s", prefix="p", mode=None)
    assert not os.path.exists(x.name)
    name = x.name
    f = open(name, "w")
    f.close()
    assert os.path.exists(name)
    del x
    gc.collect()
    assert not os.path.exists(name)
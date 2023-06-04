from subprocess import run

from bagger import Dryable


class Wasabi:

    def __init__(self, access_key: str, secret_key: str, s3host: str,
                 s3hostbucket: str, dart_hostbucket_override: bool) -> None:
        """
        Initialize Wasabi class with Wasabi connection information

        :param access_key: Wasabi access key
        :param secret_key: Wasabi secret key
        :param s3host: Wasabi s3 host
        :param s3hostbucket: Template for accessing s3 bucket
        :param dart_hostbucket_override: Override the host and bucket specified in a DART workflow
        """
        self.s3host = s3host
        self.secret_key = secret_key
        self.access_key = access_key
        self.s3hostbucket = s3hostbucket
        self.dart_hostbucket_override = dart_hostbucket_override

    def __str__(self):
        _access_key, _secret_key = 'unset', 'unset'
        if self.access_key:
            _access_key = 'set'
        if self.secret_key:
            _secret_key = 'set'

        return f"Wasabi( access_key={_access_key}, secret_key={_secret_key}, " \
               f"s3host='{self.s3host}', s3hostbucket='{self.s3hostbucket}', " \
               f"dart_hostbucket_override='{self.dart_hostbucket_override})"

    @Dryable(dry_return=('', ''))
    def list_bucket(self, folder_to_list: str) -> tuple[str, str]:
        """
        List contents of a folder within Wasabi bucket

        :param folder_to_list: Folder within bucket to list contents of
        :return: Results of ls operation on folder_to_list
        """
        cmd = ['s3cmd', '--access_key', self.access_key, '--secret_key',
               self.secret_key, '--host', self.s3host, '--host-bucket',
               self.s3hostbucket, 'ls', folder_to_list]

        ls_result = run(cmd, capture_output=True, text=True)
        return ls_result.stdout, ls_result.stderr


def get_filenames_from_ls(ls: str) -> list[str]:
    """
    Parse ls output and return filenames

    :param ls: Output of ls command to parse
    :return: List of filenames parsed from ls
    """
    lines = ls.splitlines()
    return [line.rsplit('/', 1)[-1] for line in lines if
            line.rsplit('/', 1)[-1] != '']

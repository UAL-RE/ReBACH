import sys

from subprocess import run


class Wasabi:

    def __init__(self, access_key: str, secret_key, s3host, s3hostbucket,
                 folder_to_list):
        self.folder_to_list = folder_to_list
        self.s3host = s3host
        self.secret_key = secret_key
        self.access_key = access_key
        self.s3hostbucket = s3hostbucket

    def list_bucket(self) -> str:
        cmd = ['s3cmd',
               '--access_key', self.access_key,
               '--secret_key', self.secret_key,
               '--host', self.s3host,
               '--host-bucket', self.s3hostbucket,
               'ls', self.folder_to_list
               ]

        ls_result = run(cmd, capture_output=True, text=True)
        if ls_result.stderr:
            sys.exit(f"Wasabi error: {ls_result.stderr}")

        return ls_result.stdout


def get_filenames_from_ls(ls: str) -> list[str]:
    lines = ls.splitlines()
    return [line.split('/')[-1] for line in lines if line.split('/')[-1] != '']

import sys
import requests
from typing import Any
from operator import itemgetter
from time import sleep
from ReBACH.bagger.wasabi import Wasabi, get_filenames_from_ls
import configparser


def standardize_api_result(api_result) -> dict:
    """
    Standardizes results from apis.
    Replaces null values and None with empty string in api results
    Returns a dict
    :param api_result: Result from api in json
    :type: dict
    """
    api_result_dict = api_result
    for key in api_result_dict.keys():
        if api_result_dict[key] == 'null' or api_result_dict[key] is None:
            api_result_dict[key] = ""
    return api_result_dict


def sorter_api_result(json_dict_: Any) -> Any:
    """
    Sorts a dict and its items recursively

    :param  json_dict_:  a dict or a list to be sorted
    :type: any
    :rtype: dict
    """
    sorted_dict = {}

    if not isinstance(json_dict_, dict) and not isinstance(json_dict_, list):
        return json_dict_

    if isinstance(json_dict_, list):
        if all(isinstance(item, dict) for item in json_dict_) and len(json_dict_) != 0:
            dicts_keys = [item.keys() for item in json_dict_]
            unique_dicts_keys = list({item for sublist in dicts_keys for item in sublist})
            sorted_unique_dicts_keys = sorted(unique_dicts_keys)
            return sorted(json_dict_, key=itemgetter(*sorted_unique_dicts_keys))
        return sorted(json_dict_)

    if isinstance(json_dict_, dict):
        sorted_dict = {}
        json_dict_keys = sorted(list(json_dict_.keys()))
        for key in json_dict_keys:
            sorted_dict[key] = sorter_api_result(json_dict_[key])
    return sorted_dict


def get_preserved_version_hash_and_size(config, article_id: str, version_no: int) -> tuple:
    """
    Extracts md5 hash and size from preserved article version metadata.
    If version is already preserved, it returns a tuple containing
    preserved article version md5 hash and preserved article version size
    else it returns a tuple containing empty string and 0.

    :param  config:  Configuration to use for extraction (where to extract)
    :type config: dict
    :param article_id: id number of article in Figshare
    :type article_id: str
    :param version_no: version number of article
    :type version_no: int

    :rtype: tuple
    """

    preserved_pkg_hash = ''
    preserved_pkg_size = 0
    endpoint = config['url']
    user = config['user']
    key = config['token']
    retries = int(config['retries'])
    retries_wait = int(config['retries_wait'])
    headers = {'X-Pharos-API-User': user,
               'X-Pharos-API-Key': key}
    success = False
    if 'v' in str(version_no):
        version_no = version_no
    elif int(version_no) < 10:
        version_no = f"v{str(version_no).zfill(2)}"
    else:
        version_no = f'v{str(version_no)}'

    tries = 1
    while tries <= retries and not success:
        try:
            get_preserved_pkgs = requests.get(endpoint, headers=headers, timeout=retries_wait)
            if get_preserved_pkgs.status_code == 200:
                success = True
                preserved_packages = get_preserved_pkgs.json()['results']
                for package in preserved_packages:
                    if str(article_id) in package['bag_name'] and version_no in package['bag_name']:
                        preserved_pkg_hash = package['bag_name'].split('_')[-1]
                        preserved_pkg_size = package['size']
                        return preserved_pkg_hash, preserved_pkg_size
        except requests.exceptions.RequestException as e:
            tries += 1
            print(f"Request to AP Trust failed: {e}. Retrying {tries}/{retries}...")
            if tries > retries:
                print("Max retries reached. Raising exception.")
                raise
            sleep(retries_wait)
    return preserved_pkg_hash, preserved_pkg_size


def compare_hash(article_version_hash: str, preserved_pkg_hash: str) -> bool:
    return article_version_hash == preserved_pkg_hash


def check_wasabi(article_id, version_no):
    preserved_article_hash = ''
    config = configparser.ConfigParser()
    config.read('bagger/config/default.toml')
    wasabi_config = config['Wasabi']
    wasabi_host = wasabi_config['host'].replace('\"', '')
    wasabi_bucket = 's3://' + wasabi_config['bucket'].replace('\"', '')
    wasabi_host_bucket = wasabi_config['host_bucket'].replace('\"', '')
    wasabi_access_key = wasabi_config['access_key'].replace('\"', '')
    wasabi_secret_key = wasabi_config['secret_key'].replace('\"', '')

    wasabi = Wasabi(wasabi_access_key,
                    wasabi_secret_key,
                    wasabi_host,
                    wasabi_bucket,
                    wasabi_host_bucket,
                    True
                    )

    preservation_bucket, bucket_error = wasabi.list_bucket(wasabi_bucket)

    preserved_packages = get_filenames_from_ls(preservation_bucket)

    if 'v' in str(version_no):
        version_no = version_no
    elif int(version_no) < 10:
        version_no = f"v{str(version_no).zfill(2)}"
    else:
        version_no = f'v{str(version_no)}'

    for package in preserved_packages:
        if str(article_id) in package and version_no in package:
            preserved_article_hash = package.split('_')[-1].replace('.tar', '')
            return preserved_article_hash
    return False

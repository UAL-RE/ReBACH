import requests
import json
import os
import re
from typing import Any
from time import sleep
import tempfile
from bagger.wasabi import Wasabi
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
    if isinstance(api_result_dict, dict):
        item_keys = list(api_result_dict.keys())
        for key in item_keys:
            api_result_dict[key] = standardize_api_result(api_result_dict[key])
    elif isinstance(api_result_dict, list):
        for k, v in enumerate(api_result_dict):
            api_result_dict[k] = standardize_api_result(api_result_dict[k])
    else:
        if api_result_dict == 'null' or api_result_dict is None:
            api_result_dict = ''

    return api_result_dict


def sorter_api_result(json_dict_: Any) -> Any:
    """
    Sorts a dict and its items recursively

    :param  json_dict_:  Any data type to be sorted, preferably a list or a dictionary
    :type: Any

    :return: a sorted dict or a sorted list depending on the data type of the parameter
    :rtype: dict or list
    """

    if not isinstance(json_dict_, (dict, list)):
        return json_dict_

    if isinstance(json_dict_, list):
        if all(isinstance(item, dict) for item in json_dict_) and len(json_dict_) != 0:
            dicts_keys = [key for item in json_dict_ for key in item.keys()]
            unique_dicts_keys = sorted(set(dicts_keys))

            return sorted(
                json_dict_,
                key=lambda d: tuple(
                    str(d.get(k, '')) for k in unique_dicts_keys
                )
            )
        else:
            return sorted(sorter_api_result(item) for item in json_dict_)

    if isinstance(json_dict_, dict):
        sorted_dict = {}
        json_dict_keys = sorted(json_dict_.keys())
        for key in json_dict_keys:
            if key == 'authors':
                sorted_dict[key] = json_dict_[key]
                continue
            sorted_dict[key] = sorter_api_result(json_dict_[key])
        return sorted_dict


def format_version(version_no: int) -> str:
    """
    Formats version number to v[0]{version number}

    :param version_no: version number of item
    :type: int

    :return: Formatted version number
    :rtype: str
    """
    if 'v' in str(version_no):
        version_no = version_no
    elif int(version_no) < 10:
        version_no = f"v{str(version_no).zfill(2)}"
    else:
        version_no = f'v{str(version_no)}'
    return version_no


def extract_metadata_hash_only(package_name: str) -> str:
    """
    Extracts MD5 hash of metadata from package name based on the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration.
    A package is an article bag or a collection bag.

    :param package_name: Filename of package in the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration file.
    :type: str

    :return: MD5 hash of metadata or empty string if package name format differs from the specified format
    :rtype: str
    """

    metadata_re = re.compile("[a-z0-9]{32}_bag")
    metadata_hash = metadata_re.findall(package_name)
    if len(metadata_hash) != 0:
        return metadata_hash[0].replace("_bag", '')
    return ''


def extract_version_only(package_name: str) -> str:
    """
    Extracts version from package name. A package is an article bag or a collection bag.

    :param package_name: Filename of package in the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration file.
    :type: str

    :return: Version of item bag
    :rtype: str
    """

    version_re = re.compile("-v\\d{2}-")
    version = version_re.findall(package_name)
    if len(version) != 0:
        return version[0].replace('-', '')
    return ''


def extract_item_id_only(package_name: str) -> str:
    """
    Extracts item_id from package name. A package is an article bag or a collection bag

    :param package_name: Filename of package in the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration file.
    :type: str

    :return: Item id of item bag
    :rtype: str
    """

    item_id_re = re.compile("^\\w*_\\d+-")
    item_id = item_id_re.findall(package_name)
    if len(item_id) != 0:
        return re.sub("^\\w*_", "", item_id[0]).replace('-', '')
    return ''


def extract_lastname_only(package_name: str) -> str:
    """
    Extracts author's lastname from package name. A package is an article bag or a collection bag

    :param package_name: Filename of package in the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration file.
    :type: str

    :return: Author's lastname from item bag
    :rtype: str
    """

    author_lastname_re = re.compile("-[A-Z][A-za-z]+-")
    author_last_name = author_lastname_re.findall(package_name)
    if len(author_last_name) != 0:
        return author_last_name[0].replace('-', '')
    return ''


def extract_bag_count(package_name: str) -> str:
    """
    Extracts bag count i.e "X of Y" from package name. A package is an article bag or a collection bag

    :param package_name: Filename of package in the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration file.
    :type: str

    :return: Bag count from bag name
    :rtype: str
    """

    bag_count_re = re.compile("bag[1-9]+of[1-9]+")
    bag_count = bag_count_re.findall(package_name)
    if len(bag_count) != 0:
        return bag_count[0].replace('bag', '').replace('of', ' of ')
    return ''


def extract_bag_date(package_name: str) -> str:
    """
    Extracts bag creation date in the format "YYYYMMDD" from package name. A package is an article bag or a collection bag

    :param package_name: Filename of package in the format
    [bag_name_prefix]_[article_id]-[version]-[first_author_lastname]-[metadata_hash]_bagXofY_[YYYYMMDD].
    bag_name_prefix is set in configuration file.
    :type: str

    :return: Bag creation date from bag name
    :rtype: str
    """

    bag_date_re = re.compile("\\d{8}$")
    bag_date = bag_date_re.findall(package_name)
    if len(bag_date) != 0:
        return bag_date[0]
    return ''


def get_folder_name_in_local_storage(path: str, article_id: int, version_no: int, version_hash: str) -> Any:
    """
    Gets the name of a package folder from a local storage

    :param path: Path to local storage folder
    :type path: str

    :param article_id: id number of article in Figshare
    :type article_id: int

    :param version_no: version number of article
    :type version_no: int

    :param version_hash: Version metadata Md5 hash
    :type version_hash: str

    :return: Returns the name of a package folder from a local storage if found else None.
    :rtype: None
    """

    if os.path.exists(path) and os.access(path, os.R_OK):
        folder_name_re = re.compile("\\w*_\\d+-v\\d{2}-[A-Z][A-Za-z]+-[a-z0-9]{32}_bag\\d+of\\d+_\\d{8}")
        version_no = format_version(version_no)
        for item in os.scandir(path):
            if item.is_dir() and item.name.__contains__(str(article_id)) and item.name.__contains__(version_no) \
                    and item.name.__contains__(version_hash) and folder_name_re.search(item.name) is not None:
                return item.name
    return None


def get_preserved_version_hash_and_size(config, article_id: int, version_no: int) -> list:
    """
    Extracts md5 hash and size from preserved article version metadata.
    If version is already preserved, it returns a tuple containing
    preserved article version md5 hash and preserved article version size
    else it returns a tuple containing empty string and 0.

    :param  config:  Configuration to use for extraction (where to extract)
    :type config: dict

    :param article_id: id number of article in Figshare
    :type article_id: int

    :param version_no: version number of article
    :type version_no: int

    :return: Returns a list of tuples. Each tuple contains md5 hash of the article version and
            its size if article version package exists in Wasabi else it returns empty list.
            It returns an empty list there is no preserved copy of article version.
    :rtype: list
    """

    preserved_pkg_hash = ''
    preserved_pkg_size = 0
    version_preserved_list = []
    base_url = config['url']
    user = config['user']
    key = config['token']
    item_type = "objects"
    items_per_page = int(config['items_per_page'])
    alt_id = config['alt_identifier_starts_with']
    retries = int(config['retries'])
    retries_wait = int(config['retries_wait'])
    headers = {'X-Pharos-API-User': user,
               'X-Pharos-API-Key': key}
    success = False

    if base_url[-1] != '/':
        base_url = base_url + '/'

    version_no = format_version(version_no)

    tries = 1

    while tries <= retries and not success:
        try:
            page_empty = False
            page = 1
            while not page_empty:
                endpoint = f'{base_url}{item_type}?page={page}&per_page={items_per_page}&alt_identifier__starts_with={alt_id}'
                get_preserved_pkgs = requests.get(endpoint, headers=headers, timeout=retries_wait)
                if get_preserved_pkgs.status_code == 200:
                    success = True
                    preserved_packages = get_preserved_pkgs.json()['results']
                    if preserved_packages is None:
                        page_empty = True
                    else:
                        for package in preserved_packages:
                            if str(article_id) in package['bag_name'] and version_no in package['bag_name']:
                                preserved_pkg_hash = extract_metadata_hash_only(package['bag_name'])
                                preserved_pkg_size = package['payload_size']
                                version_preserved_list.append((preserved_pkg_hash, preserved_pkg_size))
                        else:
                            page += 1
        except requests.exceptions.RequestException as e:
            tries += 1
            print(f"Request to AP Trust failed: {e}. Retrying {tries}/{retries}...")
            if tries > retries:
                print("Max retries reached. Raising exception.")
                raise
            sleep(retries_wait)
    return version_preserved_list


def compare_hash(article_version_hash: str, preserved_pkg_hash_list: list) -> bool:
    """
    Compares two strings

    :param article_version_hash: A string containing md5 hash of the current article
                               version already in AP Trust
    :type article_version_hash: str

    :param preserved_pkg_hash_list: A list of tuples. Each tuple contains md5 hash and size of the preserved copies of
                                    current article version been prepared for bagging
    :type preserved_pkg_hash_list: list

    :return: True or False
    :rtype: bool
    """

    if len(preserved_pkg_hash_list) == 0:
        return False
    for item_hash in preserved_pkg_hash_list:
        if item_hash[0] == article_version_hash:
            return True
    return False


def check_wasabi(article_id: int, version_no: int) -> list:
    """
    Checks Wasabi preservation bucket if current article version has been bagged into Wasabi

    :param article_id: Article id of current article been prepared for bagging
    :type article_id: int

    :param version_no: Version number of current article been prepared for bagging
    :type version_no: int

    :return: Returns a list of tuples. Each tuple contains md5 hash of the article version and
            its size if article version package exists in Wasabi else it returns empty list.
            It returns an empty list there is no preserved copy of article version.
    :rtype: list
    """

    preserved_article_hash = ''
    preserved_article_size = 0
    version_preserved_list = []
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

    preserved_packages = get_filenames_and_sizes_from_ls(preservation_bucket)

    version_no = format_version(version_no)

    for package in preserved_packages:
        if package[0].__contains__(str(article_id)) and package[0].__contains__(version_no):
            preserved_article_hash = extract_metadata_hash_only(package[0])
            preserved_article_size = package[1]
            version_preserved_list.append((preserved_article_hash, preserved_article_size))
    return version_preserved_list


def check_local_path(article_id: int, version_no: int, path="") -> list:
    """
    Extracts md5 hash and size from preserved article version metadata in a local storage.
    If a version is already preserved, it returns a tuple containing
    preserved article version md5 hash and preserved article version size
    else it returns a tuple containing empty string and 0.

    :param article_id: id number of an article in Figshare
    :type article_id: int

    :param version_no: version number of article
    :type version_no: int

    :param path: An accessible absolute path. It defaults to local preservation storage
    :type path: str

    :return: Returns a list of tuples. Each tuple contains md5 hash of the article version and
            its size if article version package exists in Wasabi else it returns empty list.
            It returns an empty list there is no preserved copy of article version.
    :rtype: list
    """

    if path == "":
        config = configparser.ConfigParser()
        config.read('bagger/config/default.toml')
        default_config = config['Defaults']
        path = default_config['archival_staging_storage']

    version_preserved_list = []
    preserved_article_hash = ''
    preserved_article_size = 0

    version_no = format_version(version_no)
    path = path.replace('\"', '')

    if os.path.exists(path) and os.access(path, os.R_OK):
        for item in os.scandir(path):
            if item.name.__contains__(str(article_id)) and item.name.__contains__(version_no):
                preserved_article_hash = extract_metadata_hash_only(item.name)
                preserved_article_size = os.path.getsize(item.path)
                version_preserved_list.append((preserved_article_hash, preserved_article_size))
        return version_preserved_list
    return version_preserved_list


def upload_to_remote() -> bool:
    """
    Checks if packages are uploaded to a remote storage

    :return: Return True if packages will be uploaded, otherwise False
    :rtype: bool
    """
    config = configparser.ConfigParser()
    config.read('bagger/config/default.toml')
    default_config = config['Defaults']
    workflow_file = default_config['workflow'].replace('\"', '')

    with open(workflow_file, 'r') as workflow:
        settings = json.load(workflow)
        if len(settings['storageServices']) == 0:
            return False
        return True


def get_filenames_and_sizes_from_ls(ls: str) -> list:
    """
    Extracts names of files and their sizes from ls command. It returns
    a list of tuples. Each tuple contains filename and size

    :param  ls:  Result from ls command
    :type: str

    :return: list of tuples
    :rtype: list
    """
    lines = ls.splitlines()
    return [(line.rsplit('/', 1)[-1], line.split()[-2]) for line in lines if
            line.rsplit('/', 1)[-1] != '']


def calculate_ual_rdm_size(config, article_id: int, version: str):
    """
    Calculates the size of version UAL_RDM folder

    :param  config:  Configuration to get curation storage
    :type: dict

    :param  article_id: Article ID
    :type: int

    :param  version: Article version in the 'v0{version number}'
    :type: str

    :return: Size of version UAL_RDM folder in bytes. Returns zero bytes if any of the
             folders in the path to UAL_RDM is missing
    :rtype: int
    """
    article_dir = ""
    article_version_dir = ""
    article_version_ual_rdm = ""
    version_ual_rdm_size = 0
    curation_storage = config['curation_storage_location']
    if os.path.exists(curation_storage) and os.access(curation_storage, os.R_OK):
        curation_storage_items = os.scandir(curation_storage)
        for item in curation_storage_items:
            if item.is_dir() and item.name.__contains__(str(article_id)):
                article_dir = os.path.join(curation_storage, item.name)
                break
        if not os.path.exists(article_dir):
            return 0
        for item in os.scandir(article_dir):
            if item.is_dir() and item.name.__contains__(version):
                article_version_dir = os.path.join(article_dir, item.name)
                break

        if not os.path.exists(article_version_dir):
            return 0
        for item in os.scandir(article_version_dir):
            if item.is_dir() and item.name.__contains__('UAL_RDM'):
                article_version_ual_rdm = os.path.join(article_version_dir, item.name)
                break

        if not os.path.exists(article_version_ual_rdm):
            return 0
        for item in os.scandir(article_version_ual_rdm):
            file_size = os.path.getsize(os.path.join(article_version_ual_rdm, item.name))
            version_ual_rdm_size += file_size

    return version_ual_rdm_size


def calculate_json_file_size(version_data: dict) -> int:
    """
    Pre-calculates the size of json file from Figshare version response

    :param  version_data: Version response from figshare
    :type: dict

    :return: Size of json file from Figshare version response in bytes
    :rtype: int
    """

    version_data_copy = standardize_api_result(version_data)
    version_data_copy = sorter_api_result(version_data_copy)
    version_data_copy_json = json.dumps(version_data_copy, indent=4)
    temp_dir = tempfile.gettempdir()
    filename = str(version_data['id']) + ".json"
    json_file_size = 0
    filepath = os.path.join(temp_dir, filename)
    if os.path.exists(temp_dir):
        if os.access(temp_dir, os.W_OK):
            with open(filepath, 'w') as f:
                f.write(version_data_copy_json)
            json_file_size = os.path.getsize(filepath)
            os.remove(filepath)

    return json_file_size


def calculate_payload_size(config: dict, version_data: dict) -> int:
    """
    Pre-calculates payload size for package that will be created

    :param  config:  Configuration to get curation storage
    :type: dict
    :param  version_data: Version response from figshare
    :type: dict

    :return: Size of payload in bytes. Returns zero bytes if UAL_RDM is not found
    :rtype: int
    """

    article_id = version_data['id']
    article_files_size = version_data['size']
    version_no = version_data['version']
    version = f"v{str(version_no).zfill(2)}"
    if int(version_no) > 9:
        version = f"v{str(version_no)}"
    version_ual_rdm_size = calculate_ual_rdm_size(config, article_id, version)
    if version_ual_rdm_size == 0:
        return 0
    json_file_size = calculate_json_file_size(version_data)
    payload_size = version_ual_rdm_size + json_file_size + article_files_size

    return payload_size


def get_article_id_and_version_from_path(path: str) -> tuple:
    """
    Extract article_id and version from UAL_RDM path

    :param  path:  UAL_RDM path of an article
    :type: str

    :return: A tuple containing article_id and version
    :rtype: tuple
    """
    version_no = ''
    article_id = ''
    if path:
        path_elements = path.split('/')
        version_no = path_elements[-2]
        article_id = path_elements[-3].split('_')[-1]

    return article_id, version_no


def metadata_to_hash(metadata: dict) -> dict:
    """
    Reduces an article metadata to specific metadata fields

    :param  metadata:  Complete article metadata
    :type: dict

    :return: A dictionary containing only metadata fields for hash calculation
    :rtype: dict
    """
    article_metadata = dict(metadata)
    full_metadata = list(article_metadata.keys())
    focus_metadata = ['description', 'funding_list', 'related_materials']
    for key in full_metadata:
        if key not in focus_metadata:
            del article_metadata[key]

    return article_metadata


def stringify_metadata(metadata: Any) -> str:
    """
    Concatenates all metadata field values into a string

    :param  metadata:  Item metadata in any format
    :type: Any

    :return: A string of concatenated field values
    :rtype: str
    """
    metadata_str = ""
    if isinstance(metadata, list):
        if len(metadata) == 0:
            metadata_str += ""
        else:
            for item in metadata:
                metadata_str += stringify_metadata(item)
    elif isinstance(metadata, dict):
        keys_list = sorted(list(metadata.keys()))
        for key in keys_list:
            metadata_str += stringify_metadata(metadata[key])
    else:
        metadata_str += str(metadata)

    return metadata_str

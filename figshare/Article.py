import json
import shutil
import os
import sys
import time
import requests
import hashlib
import re
from datetime import datetime
from figshare.Integration import Integration
from figshare.Utils import standardize_api_result, sorter_api_result, get_preserved_version_hash_and_size, metadata_to_hash
from figshare.Utils import compare_hash, check_wasabi, calculate_payload_size, get_article_id_and_version_from_path, stringify_metadata
from slugify import slugify
from requests.adapters import HTTPAdapter, Retry


class Article:
    api_endpoint = ""
    api_token = ""

    """
    Class constructor.
    Defined required variables that will be used in whole class.

    :param config: configuration
    :param ids: a list of ids to process. If None or an empty list is passed, all will be processed
    """
    def __init__(self, config, log, ids):
        self.config_obj = config
        figshare_config = self.config_obj.figshare_config()
        self.aptrust_config = self.config_obj.aptrust_config()
        self.system_config = self.config_obj.system_config()
        self.api_endpoint = figshare_config["url"]
        self.api_token = figshare_config["token"]
        self.bag_name_prefix = self.system_config['bag_name_prefix']
        self.bag_creation_date = datetime.today().strftime('%Y%m%d')
        self.retries = int(figshare_config["retries"]) if figshare_config["retries"] is not None else 3
        self.retry_wait = int(figshare_config["retries_wait"]) if figshare_config["retries_wait"] is not None else 10
        self.logs = log
        self.errors = []
        self.exclude_dirs = [".DS_Store"]
        self.total_all_articles_file_size = 0
        self.institution = int(figshare_config["institution"])
        self.preservation_storage_location = self.system_config["preservation_storage_location"]
        if self.preservation_storage_location[-1] != "/":
            self.preservation_storage_location = self.preservation_storage_location + "/"
        self.curation_storage_location = self.system_config["curation_storage_location"]
        if self.curation_storage_location[-1] != "/":
            self.curation_storage_location = self.curation_storage_location + "/"
        self.article_match_info = {}
        self.article_non_match_info = {}
        self.input_articles_id = ids
        self.matched_curation_folder_list = []
        self.no_matched = 0
        self.no_unmatched = 0
        self.already_preserved_counts_dict = {'already_preserved_article_ids': set(), 'already_preserved_versions': 0,
                                              'wasabi_preserved_versions': 0, 'ap_trust_preserved_versions': 0,
                                              'articles_with_error': set(), 'article_versions_with_error': 0}
        self.skipped_article_versions = {}
        self.processor = Integration(self.config_obj, self.logs)

    """
    This function is sending requests to 'account/institution/articles api.
    Static params given for pagination as page, page_size, no_of_pages.
    On successful response from above mentioned API, __get_article_versions
    will be called with article param.
    No. of tries implemented in while loop, loop will exit if API is not giving 200
    response after no. of tries defined in config file.
    """
    def get_articles(self):
        articles_api = self.api_endpoint + '/account/institution/articles'
        if self.api_endpoint[-1] == "/":
            articles_api = self.api_endpoint + "account/institution/articles"
        retries = 1
        success = False
        article_data = {}
        while not success and retries <= int(self.retries):
            try:
                # pagination implemented.
                page = 1
                page_size = 100
                page_empty = False
                self.logs.write_log_in_file("info", f"Page size is {page_size}.", True)
                while (not page_empty):
                    self.logs.write_log_in_file("info",
                                                f"Getting page {page} of articles. Total amount of pages not available.", True)
                    params = {'page': page, 'page_size': page_size, 'institution': self.institution}
                    get_response = requests.get(articles_api,
                                                headers={'Authorization': 'token ' + self.api_token},
                                                params=params,
                                                timeout=self.retry_wait
                                                )
                    if (get_response.status_code == 200):
                        articles = get_response.json()
                        if (len(articles) == 0):
                            page_empty = True
                            self.logs.write_log_in_file("info",
                                                        f"Page {page} is empty.", True)
                            break

                        if (self.input_articles_id):
                            filtered_data = [item for item in articles if item['id'] in self.input_articles_id]
                            filtered_json = json.dumps(filtered_data)
                            filtered_articles = json.loads(filtered_json)
                            article_data = self.article_loop(filtered_articles, page_size, page, article_data)
                        else:
                            article_data = self.article_loop(articles, page_size, page, article_data)

                        success = True
                    else:
                        retries = self.retries_if_error(
                            f"API is not reachable. Retry {retries}", get_response.status_code, retries)
                        if (retries > self.retries):
                            break
                    page += 1

            except Exception as e:
                retries = self.retries_if_error(e, 500, retries)
                if (retries > self.retries):
                    break

        return article_data, self.already_preserved_counts_dict

    def article_loop(self, articles, page_size, page, article_data):
        no_of_article = 0
        for article in articles:
            if (article['published_date'] is not None or article['published_date'] != ''):
                no_of_article = no_of_article + 1
                self.logs.write_log_in_file("info",
                                            f"Fetching article {no_of_article} on page {page}. ID: {article['id']}.", True)
                article_data[article['id']] = self.__get_article_versions(article)

        return article_data

    """
    This function will send request to fetch article versions.
    :param article object.
    On successful response from '/versions' API, __get_article_metadata_by_version
    will be called with version param.
    No. of tries implemented in while loop, loop will exit if API is not giving 200
    response after no. of tries defined in config file.
    """
    def __get_article_versions(self, article):
        retries = 1
        success = False

        while not success and retries <= int(self.retries):
            try:
                if (article):
                    public_url = article['url_public_api']
                    private_url = article['url_private_api']
                    version_url = public_url + "/versions"
                    get_response = requests.get(version_url)
                    if (get_response.status_code == 200):
                        versions = get_response.json()
                        metadata = []
                        if (len(versions) > 0):
                            for version in versions:
                                self.logs.write_log_in_file("info",
                                                            f"Fetching article {article['id']} version {version['version']}.", True)
                                version_data = self.__get_article_metadata_by_version(version, article['id'])
                                if version_data is None:
                                    article_version = 'v' + str(version['version']).zfill(2) if version['version'] <= 9 \
                                        else 'v' + str(version['version'])
                                    article_id = str(article['id'])
                                    self.skipped_article_versions[article_id] = []
                                    self.skipped_article_versions[article_id].append(article_version)
                                    continue
                                metadata.append(version_data)
                        else:
                            # This branch is for cases where the item has a total embargo and no versions are available via the public API
                            version_data = self.private_article_for_data(private_url, article['id'])
                            if (version_data is not None and len(version_data) > 0):
                                metadata.append(version_data)
                        success = True
                        return metadata
                    else:
                        retries = self.retries_if_error(f"Public version URL is not reachable. Retry {retries}",
                                                        get_response.status_code, retries)
                        if (retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.retries_if_error(e, 500, retries)
                if (retries > self.retries):
                    break

    def private_article_for_data(self, private_url, article_id):
        retries = 1
        success = False

        while not success and retries <= int(self.retries):
            try:
                if (private_url):
                    get_response = requests.get(private_url,
                                                headers={'Authorization': 'token ' + self.api_token},
                                                timeout=self.retry_wait)
                    if (get_response.status_code == 200):
                        version_data = get_response.json()
                        total_file_size = version_data['size']
                        files = []
                        error = ""
                        private_version_no = 0
                        if ('curation_status' in version_data and version_data['curation_status'] == 'approved'):
                            version_md5 = ''
                            json_data = json.dumps(version_data).encode("utf-8")
                            version_md5 = hashlib.md5(json_data).hexdigest()
                            files = version_data['files']
                            private_version_no = version_data['version']
                            version_metadata = self.set_version_metadata(version_data, files, private_version_no, version_md5, total_file_size)
                            version_data['total_num_files'] = len(version_data['files'])
                            version_data['file_size_sum'] = total_file_size
                            version_data['version_md5'] = version_md5
                            if (error):
                                version_metadata['errors'] = []
                                version_metadata['errors'].append(error)

                            self.logs.write_log_in_file("info", f"{version_metadata} ")

                            error = f"{version_data['id']} - This item had a total embargo. The files are from version {version_data['version']}."
                            self.logs.write_log_in_file("info", f"{error}", True)
                            return version_data
                        else:
                            error = f"{version_data['id']} - This item's curation_status was not 'approved'. It will be skipped during processing."
                            self.logs.write_log_in_file("info", f"{error}", True)
                            break
                    elif (get_response.status_code == 404):
                        res = get_response.json()
                        self.logs.write_log_in_file("info",
                                                    f"{article_id} - {res['message']}. It will be skipped during processing.")
                        break
                    else:
                        retries = self.retries_if_error(f"{article_id} Private API not reachable {private_url}. Retry {retries}",
                                                        get_response.status_code, retries)
                        if (retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.retries_if_error(f"{e}. Retry {retries}", get_response.status_code, retries)
                if (retries > self.retries):
                    break

    """
    Fetch article metadata by version url.
    :param version object value.
    :param article_id int value.
    On successful response from url_public_api API, metadata array will be setup for response.
    Metadata hash is calculated and matched against preserved version copy's has if any, if
    a match is found, the version will not be processed.
    If files aren't found and size is > 0 in public API response then
    private api will be called for files.
    No. of tries implemented in while loop, loop will exit if API is not giving
    200 response after no. of tries defined in config file.
    If files > 0 then __download_files will be called
    """
    def __get_article_metadata_by_version(self, version, article_id):
        retries = 1
        success = False
        already_preserved = in_ap_trust = False

        while not success and retries <= int(self.retries):
            try:
                if (version):
                    public_url = version['url']
                    get_response = requests.get(public_url)
                    if (get_response.status_code == 200):
                        version_data = get_response.json()
                        payload_size = calculate_payload_size(self.system_config, version_data)

                        if payload_size == 0:
                            if self.system_config['continue-on-error'] == "False":
                                self.logs.write_log_in_file("error",
                                                            f"Curation folder for article {article_id} version {version['version']} not found.",
                                                            True)
                                self.logs.write_log_in_file("info", "Aborting execution.", True, True)
                            self.already_preserved_counts_dict['articles_with_error'].add(article_id)
                            self.already_preserved_counts_dict['article_versions_with_error'] += 1
                            self.logs.write_log_in_file("error",
                                                        f"Curation folder for article {article_id} version {version['version']} not found."
                                                        + " Article version will be skipped.",
                                                        True)
                            return None

                        total_file_size = version_data['size']
                        files = []
                        error = ""
                        private_version_no = 0
                        if (total_file_size > 0 and 'files' not in version_data):
                            private_data = self.private_article_for_files(version_data)
                            files = private_data['files']
                            private_version_no = private_data['private_version_no']
                            file_len = private_data['file_len']
                            version_data['files'] = files
                        else:
                            file_len = len(version_data['files'])
                            files = version_data['files']

                        version_md5 = ''
                        version_data_for_hashing = metadata_to_hash(version_data)
                        version_data_for_hashing = standardize_api_result(version_data_for_hashing)
                        version_data_for_hashing = sorter_api_result(version_data_for_hashing)
                        str_version_data_for_hashing = stringify_metadata(version_data_for_hashing).encode("utf-8")
                        version_md5 = hashlib.md5(str_version_data_for_hashing).hexdigest()
                        version_final_storage_preserved_list = \
                            get_preserved_version_hash_and_size(self.aptrust_config, article_id, version['version'])
                        if len(version_final_storage_preserved_list) > 1:
                            self.logs.write_log_in_file("warning",
                                                        f"Multiple copies of article {article_id} version {version['version']} "
                                                        + "found in preservation final remote storage",
                                                        True)
                        version_staging_storage_preserved_list = check_wasabi(article_id, version['version'])
                        if len(version_staging_storage_preserved_list) > 1:
                            self.logs.write_log_in_file("warning",
                                                        f"Multiple copies of article {article_id} version {version['version']} "
                                                        + "found in preservation staging remote storage",
                                                        True)

                        # Compare hashes
                        # Checking both remote storages
                        if compare_hash(version_md5, version_staging_storage_preserved_list) and \
                                compare_hash(version_md5, version_final_storage_preserved_list):
                            already_preserved = in_ap_trust = True
                            self.already_preserved_counts_dict['already_preserved_versions'] += 1
                            self.already_preserved_counts_dict['wasabi_preserved_versions'] += 1
                            self.already_preserved_counts_dict['ap_trust_preserved_versions'] += 1
                            self.logs.write_log_in_file("info",
                                                        f"Article {article_id} version {version['version']} "
                                                        + "already preserved in preservation staging remote storage"
                                                        + " and preservation final remote storage.",
                                                        True)

                        elif compare_hash(version_md5, version_staging_storage_preserved_list):  # Preservation staging remote storage only check
                            already_preserved = True
                            in_ap_trust = False
                            self.already_preserved_counts_dict['already_preserved_versions'] += 1
                            self.already_preserved_counts_dict['wasabi_preserved_versions'] += 1
                            self.logs.write_log_in_file("info", f"Article {article_id} version {version['version']} "
                                                                + "already preserved in preservation staging remote storage.",
                                                        True)

                        elif compare_hash(version_md5, version_final_storage_preserved_list):  # Preservation final remote storage only check
                            already_preserved = in_ap_trust = True
                            self.already_preserved_counts_dict['already_preserved_versions'] += 1
                            self.already_preserved_counts_dict['ap_trust_preserved_versions'] += 1
                            self.logs.write_log_in_file("info",
                                                        f"Article {article_id} version {version['version']} "
                                                        + "already preserved in preservation final remote storage.",
                                                        True)

                        if already_preserved:
                            self.already_preserved_counts_dict['already_preserved_article_ids'].add(article_id)
                            if in_ap_trust:
                                for version_hash in version_final_storage_preserved_list:
                                    if version_hash[0] == version_md5 and version_hash[1] != payload_size:
                                        self.logs.write_log_in_file("warning",
                                                                    f"Article {article_id} version {version['version']} "
                                                                    + "found in preservation final remote storage but sizes do not match.",
                                                                    True)
                            return None

                        version_metadata = self.set_version_metadata(version_data, files, private_version_no, version_md5, total_file_size)
                        version_data['total_num_files'] = file_len
                        version_data['file_size_sum'] = total_file_size
                        version_data['version_md5'] = version_md5

                        if error:
                            version_metadata['errors'] = []
                            version_metadata['errors'].append(error)

                        self.logs.write_log_in_file("info", f"{version_metadata} ")

                        return version_data
                    else:
                        retries = self.retries_if_error(f"{article_id} Public API not reachable. Retry {retries}",
                                                        get_response.status_code, retries)
                        if (retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.retries_if_error(f"{e}. Retry {retries}", get_response.status_code, retries)
                if (retries > self.retries):
                    break

    def set_version_metadata(self, version_data, files, private_version_no, version_md5, total_file_size):
        # item_subtype conditions
        sub_type = ''
        if (version_data['has_linked_file']):
            sub_type = 'linked'
        elif (version_data['is_metadata_record']):
            sub_type = 'metadata'
        else:
            sub_type = 'regular'
        return {'article_id': version_data['id'],
                'metadata': {
                    'item_type': 'article', 'item_subtype': sub_type,
                    'id': version_data['id'], 'version': version_data['version'],
                    'first_author': version_data['authors'][0], 'files': files,
                    'total_num_files': len(files), 'file_size_sum': total_file_size,
                    'public_url': version_data['url_public_api'],
                    'private_version_no': private_version_no,
                    'md5': version_md5
                    }
                }

    def private_article_for_files(self, version_data):
        get_response = requests.get(version_data['url_private_api'],
                                    headers={'Authorization': 'token ' + self.api_token},
                                    timeout=self.retry_wait)
        file_len = 0
        files = []
        private_version_no = 0
        if (get_response.status_code == 200):
            version_data_private = get_response.json()
            # checking curation_status from article's private api
            if ('curation_status' in version_data_private and version_data_private['curation_status'] == "approved"):
                file_len = len(version_data_private['files'])
                files = version_data_private['files']
                private_version_no = version_data_private['version']
                error = f"{version_data['id']} - This item had a file embargo." \
                        + f" The files are from version {str(private_version_no)}."
                self.logs.write_log_in_file("info", f"{error}", True)
            else:
                error = f"{version_data['id']} - This item's curation_status was not 'approved'. It will be skipped during processing."
                self.logs.write_log_in_file("info", f"{error}", True)

        return {"files": files, "private_version_no": private_version_no, "file_len": file_len}

    """
    This function will download files and place them in directory, with version_metadata.
    """
    def __download_files(self, files, version_data, folder_name):
        delete_folder = False
        self.logs.write_log_in_file('info', "Downloading files.", True)

        retry_strategy = Retry(
            total=self.retries,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)

        if (len(files) > 0):
            version_no = "v" + str(version_data["version"]).zfill(2)
            article_folder = folder_name + "/" + version_no
            file_no = 0
            for file in files:
                if (file['is_link_only'] is False):
                    article_files_folder = article_folder + "/DATA"
                    preservation_storage_location = self.preservation_storage_location
                    article_folder_path = preservation_storage_location + article_files_folder
                    article_files_path_exists = os.path.exists(article_folder_path)
                    if (article_files_path_exists is False):
                        os.makedirs(article_folder_path, exist_ok=True)

                    file_name_with_path = article_folder_path + "/" + str(file['id']) + "_" + file['name']
                    self.logs.write_log_in_file("info",
                                                f"Downloading file {file['id']} for article {version_data['id']} - "
                                                + f"version {version_data['version']}", True)

                    status_code = -1
                    with http.get(file['download_url'], stream=True, allow_redirects=True,
                                  headers={'Authorization': 'token ' + self.api_token}) as r:
                        r.raise_for_status()
                        try:
                            with open(file_name_with_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            status_code = r.status_code
                        except requests.exceptions.HTTPError as e:
                            status_code = e.response.status_code
                        except Exception as e:
                            status_code = -1
                            self.logs.write_log_in_file("error", str(e), True)

                    if (status_code == 200):
                        file_no = file_no + 1
                        self.logs.write_log_in_file("info", "Checking hash")
                        existing_file_hash = self.__get_single_file_hash(file_name_with_path)
                        compare_hash = file['supplied_md5']
                        if (compare_hash == ""):
                            compare_hash = file['computed_md5']

                        if (existing_file_hash != compare_hash):
                            self.logs.write_log_in_file("error",
                                                        f"{version_data['id']} version {version_data['version']} - Hash didn't "
                                                        + f"match after downloading: Filename {file['name']}. Folder will be deleted.", True)
                            delete_folder = True
                            break
                        else:
                            self.logs.write_log_in_file("info", "Download ok", True)
                    else:
                        self.logs.write_log_in_file("error",
                                                    f"{version_data['id']} version {version_data['version']} - File couldn't download. Status "
                                                    + f"code {status_code}. Filename {file['name']}. Folder will be deleted.", True)
                        delete_folder = True
                        break
        else:
            self.logs.write_log_in_file("info", "No files to download.", True)

        return delete_folder

    """
    Retries function.
    :param msg
    :param status_code
    :param retries
    :return retries
    """
    def retries_if_error(self, msg, status_code, retries):
        self.logs.write_log_in_file("error", f"{msg} - Status code {status_code}", True)
        wait = self.retry_wait
        self.logs.write_log_in_file("error", 'Error! Waiting %s secs and re-trying...' % wait, True)
        sys.stdout.flush()
        time.sleep(wait)
        retries = int(retries) + 1
        return retries

    """
    Checks curation directory, if required files are found, copies all files to temp directory on root of the script
    :param version_data dictionary
    """
    def __check_curation_dir(self, version_data):
        curation_storage_location = self.curation_storage_location
        dirs = os.listdir(curation_storage_location)
        version_no = "v" + str(version_data["version"]).zfill(2)
        version_data["matched"] = False
        for dir in dirs:
            if (dir not in self.exclude_dirs):
                dir_array = dir.split("_")
                # check author name with article id directory exists like 'John_Smith_546187'
                author_dir = dir
                if (str(version_data['id']) in dir_array):
                    article_dir_in_curation = curation_storage_location + dir
                    # read author dir
                    read_dirs = os.listdir(article_dir_in_curation)
                    version_data["curation_info"] = {}
                    for dir in read_dirs:
                        if dir not in self.exclude_dirs:
                            if (dir == version_no):
                                version_dir = article_dir_in_curation + "/" + dir
                                # read version dir
                                read_version_dirs = os.listdir(version_dir)
                                version_data["matched"] = is_matched = True
                                version_data['author_dir'] = author_dir
                                # item_subtype conditions
                                sub_type = ''
                                if (version_data['has_linked_file']):
                                    sub_type = 'linked'
                                elif (version_data['is_metadata_record']):
                                    sub_type = 'metadata'
                                else:
                                    sub_type = 'regular'
                                version_data["curation_info"] = {'item_type': 'article', 'item_subtype': sub_type,
                                                                 'id': version_data['id'], 'version': version_data['version'],
                                                                 'first_author': version_data['authors'][0]['full_name'], 'url': version_data['url'],
                                                                 'md5': version_data['version_md5'], 'path': version_dir,
                                                                 'total_files': version_data['total_num_files'],
                                                                 'total_files_size': version_data['file_size_sum'],
                                                                 'is_matched': is_matched
                                                                 }
                                # article version data with curation info saved in logs.
                                self.logs.write_log_in_file("info", f"{version_data} ")

                                # check if UAL_RDM dir exists
                                if "UAL_RDM" not in read_version_dirs:
                                    self.logs.write_log_in_file("error",
                                                                f"{version_data['id']} version {version_data['version']} - UAL_RDM directory "
                                                                + "missing in curation storage. Path is {version_dir}", True)
                                    break
                                else:
                                    version_data = self.read_version_dirs_fun(read_version_dirs, version_dir, version_data)

        return version_data

    def read_version_dirs_fun(self, read_version_dirs, version_dir, version_data):
        deposit_agreement_file = False
        redata_deposit_review_file = False
        trello_file = False
        for dir in read_version_dirs:
            if dir not in self.exclude_dirs:
                if dir == "UAL_RDM":
                    ual_rdm_path = version_dir + "/" + dir
                    ual_dir = os.listdir(ual_rdm_path)
                    for ual_file in ual_dir:
                        if ("Deposit Agreement".lower() in ual_file.lower()
                                or "Deposit_Agreement".lower() in ual_file.lower()):
                            deposit_agreement_file = True

                        if ("ReDATA-DepositReview".lower() in ual_file.lower()):
                            redata_deposit_review_file = True

                        if (ual_file.lower().endswith("trello.pdf")):
                            trello_file = True

        version_data["deposit_agreement_file"] = deposit_agreement_file
        version_data["redata_deposit_review_file"] = redata_deposit_review_file
        version_data["trello_file"] = trello_file

        return version_data

    """
    Get size of files of the given directory path, excluding skipped articles UAL_RDM
    :param dir_path string  path of dir where file size require to calculate.
    :param include_only string include in the total only paths that contain this string. If ommitted, includes all paths.
    :return size integer
    """
    def get_file_size_of_given_path(self, dir_path, include_only=""):
        size = 0
        for path, dirs, files in os.walk(dir_path):
            if include_only in path:
                article_id, article_version = get_article_id_and_version_from_path(path)
                if article_id in self.skipped_article_versions.keys() and article_version in self.skipped_article_versions[article_id]:
                    size += 0
                else:
                    for f in files:
                        fp = os.path.join(path, f)
                        try:
                            size += os.path.getsize(fp)
                        except Exception:
                            pass

        return size

    """
    Compare the required space with available space
    :param required_space integer
    :return log error and terminate script if required_space greater.
    """
    def check_required_space(self, required_space):
        self.logs.write_log_in_file("info", "Checking required space, script might stop if there's not enough space.", True)
        req_space = required_space * (1 + (int(self.system_config["additional_percentage_required"]) / 100))
        preservation_storage_location = self.preservation_storage_location
        memory = shutil.disk_usage(preservation_storage_location)
        available_space = memory.free
        if (req_space > available_space):
            if self.system_config['continue-on-error'] == "False":
                self.logs.write_log_in_file('error', "There isn't enough space in storage path."
                                            + f"Required space is {req_space} and available space is {available_space}. Aborting...",
                                            True, True)
            self.logs.write_log_in_file('error', "There isn't enough space in storage path."
                                        + f"Required space is {req_space} and available space is {available_space}.",
                                        True)

    """
    Checking file hash
    :param files dictionary
    :param version_data dictionary
    :param folder_path string
    :return boolean
    """
    def __check_file_hash(self, files, version_data, folder_path):
        version_no = "v" + str(version_data["version"]).zfill(2)
        article_version_folder = folder_path + "/" + version_no
        article_files_folder = article_version_folder + "/DATA"
        preservation_storage_location = self.preservation_storage_location
        article_folder_path = preservation_storage_location + article_files_folder

        # check if preservation dir is reachable
        self.check_access_of_directories(preservation_storage_location, "preservation")

        article_files_path_exists = os.path.exists(article_folder_path)
        process_article = False
        delete_folder = False

        if (article_files_path_exists is True):
            get_files = os.listdir(article_folder_path)
            if (len(get_files) > 0):
                self.logs.write_log_in_file('info', "Comparing Figshare file hashes against existing local files.", True)
                for file in files:
                    file_path = article_folder_path + "/" + str(file['id']) + "_" + file['name']
                    file_exists = os.path.exists(file_path)
                    compare_hash = file['supplied_md5']
                    if (compare_hash == ""):
                        compare_hash = file['computed_md5']

                    if (file_exists is True):
                        # checking md5 values to check if existing file is same or not.
                        existing_file_hash = self.__get_single_file_hash(file_path)
                        if (existing_file_hash != compare_hash):
                            delete_folder = True
                            self.logs.write_log_in_file('error', f"{file_path} hash does not match.", True)
                            break
                        else:
                            self.logs.write_log_in_file('info', f"{file_path.replace(preservation_storage_location + article_files_folder, '')} "
                                                        + "file exists (hash match).", True)
                        process_article = False
                    else:
                        self.logs.write_log_in_file('error', f"{file_path} does not exist.", True)
                        delete_folder = True
                        process_article = False
                        break
            else:
                self.logs.write_log_in_file("info", f"{article_folder_path} is empty, nothing to check.", True)
                process_article = True

        else:
            self.logs.write_log_in_file("info", f"{article_folder_path} not found, nothing to check.", True)
            process_article = True

        # delete directory if validation failed.
        if (delete_folder is True):
            self.logs.write_log_in_file("error", f"Validation failed, deleting {preservation_storage_location + folder_path}.", True)
            if self.system_config['dry-run'] == 'False':
                self.delete_folder(preservation_storage_location + folder_path)
            else:
                self.logs.write_log_in_file("info", "*Dry Run* Folder not deleted.", True)
            process_article = True

        return process_article

    def __get_single_file_hash(self, filepath):
        """
        Calculates the has of the given file. Calculation is chunked to save memory
        :param filepath string
        :return string
        """
        hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), ""):
                if (chunk):
                    hash.update(chunk)
                else:
                    break
        return hash.hexdigest()

    """
    Save json data for each article in related directory
    :param version_data dictionary
    :param folder_name string
    """
    def __save_json_in_metadata(self, version_data, folder_name):
        result = False

        version_no = "v" + str(version_data["version"]).zfill(2)
        json_folder_path = folder_name + "/" + version_no + "/METADATA"
        preservation_storage_location = self.preservation_storage_location
        complete_path = preservation_storage_location + json_folder_path
        check_path_exists = os.path.exists(complete_path)
        try:
            if (check_path_exists is False):
                os.makedirs(complete_path, exist_ok=True)
            # Remove extra indexes from version data before saving in json file
            # These indexes were created in code while fetching data from APIs for further processing
            if ("matched" in version_data):
                del (version_data["matched"])
            if ("curation_info" in version_data):
                del (version_data["curation_info"])
            if ("total_num_files" in version_data):
                del (version_data["total_num_files"])
            if ("file_size_sum" in version_data):
                del (version_data["file_size_sum"])
            if ("version_md5" in version_data):
                del (version_data["version_md5"])
            if ("redata_deposit_review_file" in version_data):
                del (version_data["redata_deposit_review_file"])
            if ("deposit_agreement_file" in version_data):
                del (version_data["deposit_agreement_file"])
            if ("trello_file" in version_data):
                del (version_data["trello_file"])
            if ("author_dir" in version_data):
                del (version_data["author_dir"])
            json_data = json.dumps(version_data, indent=4)
            filename_path = complete_path + "/" + str(version_data['id']) + ".json"
            # Writing to json file
            with open(filename_path, "w") as outfile:
                outfile.write(json_data)
            result = True
        except Exception as e:
            self.logs.write_log_in_file('error', f"{folder_name}: {e}", True)
            result = False

        if not result:
            self.logs.write_log_in_file("info", "json not saved.", True)
        return result

    """
    Copying UAL_RDM folder files to storage directory in related article version folder
    :param version_data dictionary
    :param folder_name string
    """
    def __copy_files_ual_rdm(self, version_data, folder_name):
        result = False

        version_no = "v" + str(version_data["version"]).zfill(2)
        curation_storage_location = self.curation_storage_location
        # check curation dir is reachable
        self.check_access_of_directories(curation_storage_location, "curation")

        preservation_storage_location = self.preservation_storage_location
        complete_folder_name = os.path.join(preservation_storage_location, folder_name, version_no, "UAL_RDM")
        dirs = os.listdir(curation_storage_location)
        for dir in dirs:
            if (dir not in self.exclude_dirs):
                dir_array = dir.split("_")
                # check author name with article id directory exists like 'John_Smith_546187'
                if (str(version_data['id']) in dir_array):
                    article_dir_in_curation = curation_storage_location + dir
                    # read author dir
                    read_dirs = os.listdir(article_dir_in_curation)
                    for dir in read_dirs:
                        if dir not in self.exclude_dirs:
                            if (dir == version_no):
                                curation_dir_name = os.path.join(article_dir_in_curation, dir, "UAL_RDM")
                                # check preservation dir is reachable
                                self.check_access_of_directories(preservation_storage_location, "preservation")
                                try:
                                    check_path_exists = os.path.exists(complete_folder_name)
                                    if (check_path_exists is False):
                                        os.makedirs(complete_folder_name, exist_ok=True)
                                    # copying files to preservation version folder
                                    shutil.copytree(curation_dir_name, complete_folder_name, dirs_exist_ok=True, ignore_dangling_symlinks=False)
                                    self.logs.write_log_in_file("info", "Copied curation files to preservation folder.", True)
                                    result = True
                                except Exception as e:
                                    self.logs.write_log_in_file('error', f"{e} - {complete_folder_name}.", True)
                                    result = False
        if not result:
            self.logs.write_log_in_file("info", "No files copied to preservation folder.", True)
        return result

    """
    Find matched articles from the fetched data and curation dir
    """
    def find_matched_articles(self, articles):
        article_data = {}
        self.no_matched = 0
        self.no_unmatched = 0
        i = 0
        for article in articles:
            if (articles[article] is not None):
                article_versions_list = articles[article]
                article_data[article] = []
                for version_data in article_versions_list:
                    # check curation folder for required files and setup data for further processing.
                    if (version_data is not None and len(version_data) > 0):
                        data = self.__check_curation_dir(version_data)
                        version_no = "v" + str(data["version"]).zfill(2)
                        i += 1
                        if (data["matched"] is True):
                            total_file_size = version_data['size']
                            self.total_all_articles_file_size += total_file_size
                            article_data[version_data['id']].append(data)
                            self.no_matched += 1
                            self.article_match_info[i] = f"article {data['id']} {version_no} ----- {data['author_dir']}"
                            if (self.input_articles_id):
                                self.matched_curation_folder_list.append(os.path.join(data['author_dir'], version_no))
                        else:
                            self.article_non_match_info[i] = f"article {data['id']} {version_no}"

        matched_articles = []
        if (self.article_match_info):
            self.logs.write_log_in_file('info', "Curation folder found for below articles", True)

            # log articles id, version and dir name if matched.
            for index in self.article_match_info:
                self.logs.write_log_in_file('info', self.article_match_info[index], True)

                matched_id = re.search(r'article\s(.*?)\sv0', self.article_match_info[index])
                if matched_id:
                    matched_article_id = matched_id.group(1).strip()
                    matched_articles.append(matched_article_id)
                else:
                    self.logs.write_log_in_file('error', f"Unable to fetch matched article id - {self.article_match_info[index]}", True)

        unmatched_articles = []
        self.no_unmatched = len(self.article_non_match_info)
        if (self.article_non_match_info):
            self.logs.write_log_in_file('info', "Curation folder not found for below articles", True)

            # log unmatched articles id, and version
            for index in self.article_non_match_info:
                self.logs.write_log_in_file('info', self.article_non_match_info[index], True)

                unmatched_id = re.search(r'article\s(.*?)\sv0', self.article_non_match_info[index])
                if unmatched_id:
                    unmatched_article_id = unmatched_id.group(1).strip()
                    unmatched_articles.append(unmatched_article_id)
                else:
                    self.logs.write_log_in_file('error', f"Unable to fetch unmatched article id - {self.article_non_match_info[index]}", True)

        self.logs.write_log_in_file("info", f"Total matched unique articles: {len(set(matched_articles))}.", True)
        self.logs.write_log_in_file("info", f"Total unmatched unique articles: {len(set(unmatched_articles))}.", True)
        self.logs.write_log_in_file("info", f"Total matched article versions: {self.no_matched}.", True)
        self.logs.write_log_in_file("info", f"Total unmatched article versions: {self.no_unmatched}.", True)
        self.logs.write_log_in_file("info", "Total skipped unique articles: "
                                    + f"{len(self.already_preserved_counts_dict['already_preserved_article_ids'])}.", True)
        self.logs.write_log_in_file("info", "Total skipped article versions: "
                                    + f"{self.already_preserved_counts_dict['already_preserved_versions']}.", True)

        if len(set(unmatched_articles)) > 0 or len(self.article_non_match_info) > 0:
            self.logs.write_log_in_file("warning", "There were unmatched articles or article versions."
                                        + f"Check {self.curation_storage_location} for each of the unmatched items.", True)

        return article_data

    """
    Check files are copyable or not
    """
    def __can_copy_files(self, version_data):
        if (version_data["deposit_agreement_file"] is False
                or version_data["redata_deposit_review_file"] is False
                or version_data["trello_file"] is False):
            self.logs.write_log_in_file("error", f"{version_data['id']} version {version_data['version']} - UAL_RDM directory doesn't have required "
                                        + "files in curation storage. Folder will be deleted.", True)
            copy_files = False
        else:
            self.logs.write_log_in_file("info", "Curation files exist. Continuing execution.", True)
            copy_files = True

        return copy_files

    """
    Final process for matched articles. Returns True if succeeded.
    """
    def __final_process(self, check_files, copy_files, check_dir, version_data, folder_name, version_no, value_pre_process):
        success = True
        if copy_files and not check_files:
            # check and create empty directories for each version
            self.logs.write_log_in_file("info", "Checking and creating empty directories in preservation storage.", True)
            success = success & self.create_required_folders(version_data, folder_name)
            # copy curation UAL_RDM files in storage UAL_RDM folder for each version
            self.logs.write_log_in_file("info", "Copying curation UAL_RDM files to preservation UAL_RDM folder.", True)
            success = success & self.__copy_files_ual_rdm(version_data, folder_name)
            # save json in metadata folder for each version
            self.logs.write_log_in_file("info", "Saving json in metadata folder for each version.", True)
            success = success & self.__save_json_in_metadata(version_data, folder_name)

        if check_files and copy_files:
            try:
                # download all files and verify hash with downloaded file.
                delete_now = self.__download_files(version_data['files'], version_data, folder_name)
            except Exception as e:
                self.logs.write_log_in_file("error", f"{str(e)} for {'_'.join(os.path.basename(folder_name).split('_')[0:-1])}" , True)
                if self.system_config['continue-on-error'] == "False":
                    self.logs.write_log_in_file("info", "Aborting execution.", True, True)
                delete_now = True

            # check if download process has error or not.
            if (delete_now is False):
                # copy curation UAL_RDM files in storage UAL_RDM folder for each version
                self.logs.write_log_in_file("info", "Copying curation UAL_RDM files to preservation UAL_RDM folder for each version.", True)
                success = success & self.__copy_files_ual_rdm(version_data, folder_name)
                # check and create empty directories for each version
                self.logs.write_log_in_file("info", "Checking and creating empty directories for each version.", True)
                success = success & self.create_required_folders(version_data, folder_name)
                # save json in metadata folder for each version
                self.logs.write_log_in_file("info", "Saving json in metadata folder for each version.", True)
                success = success & self.__save_json_in_metadata(version_data, folder_name)

                # only run the postprocessor if all above steps succeeded
                if success:
                    value_post_process = self.processor.post_process_script_function("Article", check_dir, value_pre_process)
                    if (value_post_process != 0):
                        self.logs.write_log_in_file("error",
                                                    f"{version_data['id']} version {version_data['version']} - Post-processing script failed.",
                                                    True)
                        success = False
                    else:
                        success = True
                else:
                    self.logs.write_log_in_file("info",
                                                f"No further processing for {version_data['id']} version {version_data['version']} due to errors.",
                                                True)
                    success = False
            else:
                # if download process has any errors then delete complete folder
                self.logs.write_log_in_file("info", "Download process had an error so complete folder is being deleted.", True)
                self.delete_folder(check_dir)
                success = False
        else:
            if check_files or copy_files:
                if success:
                    # call post process script function for each matched item.
                    value_post_process = self.processor.post_process_script_function("Article", check_dir, value_pre_process)
                    if (value_post_process != 0):
                        self.logs.write_log_in_file("error",
                                                    f"{version_data['id']} version {version_data['version']} - Post-processing script failed.",
                                                    True)
                        success = False
                    else:
                        success = True
                else:
                    self.logs.write_log_in_file("info",
                                                f"No further processing for {version_data['id']} version {version_data['version']} due to errors.",
                                                True)
                    success = False
            else:
                self.logs.write_log_in_file("error", "Unexpected condidion in final processing. No further actions taken.", True)
                success = False
        return success

    """
    Called before articles processing.
    """
    def __initial_process(self):
        # get curation directory path
        curation_storage_location = self.curation_storage_location
        # get preservation directory path
        preservation_storage_location = self.preservation_storage_location
        # curation dir is reachable
        self.check_access_of_directories(curation_storage_location, "curation")

        # preservation dir is reachable
        self.check_access_of_directories(preservation_storage_location, "preservation")

        return curation_storage_location

    """
    Process all articles after fetching from API. Returns the number of successfully processed articles.
    """
    def process_articles(self, articles):
        processed_count = 0
        curation_storage_location = self.__initial_process()
        self.logs.write_log_in_file("info", "------- Processing articles -------", True)
        self.logs.write_log_in_file("info", "Finding matched articles.", True)
        article_data = self.find_matched_articles(articles)

        # Calculate the size of the curation folder
        # When article IDs are explicitly passed, curation folder size is calculated based on matched curation folders.
        # Otherwise, it is calculated considering all curation folders.
        # Size of curation folders for skipped articles are excluded in all cases.
        if (self.matched_curation_folder_list):
            curation_folder_size = 0
            for folder in self.matched_curation_folder_list:
                path = curation_storage_location + folder
                curation_folder_size += self.get_file_size_of_given_path(path, "UAL_RDM")
        elif len(self.matched_curation_folder_list) == 0 and len(article_data) != 0:
            curation_folder_size = 0
        else:
            curation_folder_size = self.get_file_size_of_given_path(curation_storage_location, "UAL_RDM")

        required_space = curation_folder_size + self.total_all_articles_file_size

        self.logs.write_log_in_file("info", f"Total size of articles to be processed: {self.total_all_articles_file_size} bytes", True)
        self.logs.write_log_in_file("info", f"Total size of the curated folders for the matched articles: {curation_folder_size} bytes", True)
        self.logs.write_log_in_file("info", f"Total space required: {required_space} bytes", True)

        # check required space after curation process, it will stop process if there isn't sufficient space.
        self.check_required_space(required_space)

        for article in article_data:
            article_versions_list = article_data[article]
            for version_data in article_versions_list:
                if version_data is not None or len(version_data) > 0:
                    version_no = "v" + str(version_data["version"]).zfill(2)
                    first_depositor_last_name = version_data['authors'][0]['last_name'].replace('-','')
                    formatted_depositor_full_name = slugify(first_depositor_last_name, separator="_", lowercase=False)
                    folder_name = self.bag_name_prefix + "_" + str(version_data["id"]) + "-" + version_no + "-" \
                        + formatted_depositor_full_name + "-" + version_data['version_md5'] + "_bag_" + str(self.bag_creation_date)

                    if (version_data["matched"] is True):
                        self.logs.write_log_in_file("info", f"------- Processing article {article} version {version_data['version']}.", True)

                        # call pre process script function for each matched item.
                        if self.system_config['dry-run'] == 'False':
                            value_pre_process = self.pre_process_script_function()
                        else:
                            value_pre_process = 0
                            self.logs.write_log_in_file("info", "*Dry Run* Skipping pre processing.", True)

                        if (value_pre_process == 0):
                            self.logs.write_log_in_file("info", "Pre-processing script finished successfully.", True)
                            # check main folder exists in preservation storage.
                            preservation_storage_location = self.preservation_storage_location
                            check_dir = preservation_storage_location + folder_name
                            check_files = True
                            copy_files = True
                            self.logs.write_log_in_file("info", f"Checking if {check_dir} exists.", True)
                            if (os.path.exists(check_dir) is True):
                                get_dirs = os.listdir(check_dir)
                                if (len(get_dirs) > 0):
                                    self.logs.write_log_in_file("info", "Exists and is not empty, checking contents.", True)
                                    check_files = self.__check_file_hash(version_data['files'], version_data, folder_name)
                                else:
                                    self.logs.write_log_in_file("info", "Exists and is empty", True)
                                    check_files = False

                                    if self.system_config['dry-run'] == 'False':
                                        # delete folder if validation fails
                                        self.delete_folder(check_dir)
                                        # call post process script function for each matched item. Code 5 corresponds to step 5 of S4.4 in the spec.
                                        value_post_process = self.processor.post_process_script_function("Article", check_dir, value_pre_process, 5)
                                        if (value_post_process != 0):
                                            self.logs.write_log_in_file("error", f"{version_data['id']} version {version_data['version']} - "
                                                                        + "Post-processing script error found.", True)
                                    else:
                                        self.logs.write_log_in_file("info", "*Dry Run* File download and post-processing with "
                                                                    + f"{self.system_config['post_process_script_command']} skipped.", True)

                                    break
                            else:
                                value_post_process = 0
                                if self.system_config['dry-run'] == 'False':
                                    self.logs.write_log_in_file("info", "Does not exist. Folder will be created", True)
                                else:
                                    self.logs.write_log_in_file("info", "*Dru Run* Does not exist. Folder will not be created", True)

                            # end check main folder exists in preservation storage.
                            # check required files exist in curation UAL_RDM folder
                            self.logs.write_log_in_file("info", "Checking required files exist in associated curation "
                                                        + f"folder {curation_storage_location}.", True)
                            copy_files = self.__can_copy_files(version_data)

                            if self.system_config['dry-run'] == 'False':
                                if self.__final_process(check_files, copy_files, check_dir, version_data, folder_name, version_no, value_pre_process):
                                    processed_count += 1
                            else:
                                processed_count += 1
                                self.logs.write_log_in_file("info", "*Dry Run* File download and post-processing with "
                                                            + f"{self.system_config['post_process_script_command']} skipped.", True)
                        else:
                            self.logs.write_log_in_file("error", "Pre-processing script failed. Running post-processing script.", True)
                            # call post process script function for each matched item.
                            value_post_process = self.processor.post_process_script_function("Article", check_dir, value_pre_process)
                            if (value_post_process != 0):
                                self.logs.write_log_in_file("error", f"{version_data['id']} version {version_data['version']} - "
                                                            + "Post-processing script failed.", True)
        return processed_count, self.already_preserved_counts_dict['ap_trust_preserved_versions'], \
            self.already_preserved_counts_dict['wasabi_preserved_versions']

    """
    Preservation and Curation directory access check while processing.
    Retries also implemented.
    :param directory_path string
    :param process_name string
    """
    def check_access_of_directories(self, directory_path, process_name="preservation"):
        success = False
        retries = 1
        while not success and retries <= int(self.retries):
            path_exists = os.path.exists(directory_path)
            folder_access = os.access(directory_path, os.R_OK)
            text = "curation storage"
            if (process_name == "preservation"):
                text = "preservation storage"
            if (path_exists is False or folder_access is False):
                retries = self.retries_if_error(f"The {text} location specified in the config file could"
                                                + f" not be reached or read. Retry {retries}.", 500, retries)
                if (retries > self.retries):
                    exit()
            else:
                success = True

    def create_required_folders(self, version_data, folder_name):
        preservation_storage_location = self.preservation_storage_location
        version_no = "v" + str(version_data["version"]).zfill(2)
        # setup UAL_RDM directory
        ual_folder_name = preservation_storage_location + folder_name + "/" + version_no + "/UAL_RDM"
        ual_path_exists = os.path.exists(ual_folder_name)
        try:
            if (ual_path_exists is False):
                # create UAL_RDM directory if not exist
                os.makedirs(ual_folder_name, exist_ok=True)
            else:
                self.logs.write_log_in_file("info", "UAL_RDM directory already exists. Folder not created", True)

            # setup DATA directory
            data_folder_name = preservation_storage_location + folder_name + "/" + version_no + "/DATA"
            data_path_exists = os.path.exists(data_folder_name)
            if (data_path_exists is False):
                # create DATA directory if it does not exist
                os.makedirs(data_folder_name, exist_ok=True)
            else:
                self.logs.write_log_in_file("info", "DATA directory already exists. Folder not created", True)
        except Exception as e:
            self.logs.write_log_in_file('error', f"{folder_name}: {e}", True)
            return False
        return True

    """
    Pre-processing script command function.
    """
    def pre_process_script_function(self):
        pre_process_script_command = self.system_config["pre_process_script_command"]
        if (pre_process_script_command != ""):
            self.logs.write_log_in_file("info", f"Executing pre-processing script: {pre_process_script_command}.", True)
        else:
            return 0

    """
    Delete folder
    """
    def delete_folder(self, folder_path):
        check_exists = os.path.exists(folder_path)
        if (check_exists is True):
            shutil.rmtree(folder_path)
            self.logs.write_log_in_file("info", f"{folder_path} deleted due to failed validations.", True)

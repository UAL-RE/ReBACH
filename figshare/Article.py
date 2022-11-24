import json
# import math
import shutil
import os
import sys
import time
import requests
from Log import Log
from Config import Config
import hashlib


class Article:
    api_endpoint = ""
    api_token = ""

    """
    Class constructor.
    Defined requried variables that will be used in whole class.
    """
    def __init__(self, config):
        self.config_obj = Config(config)
        figshare_config = self.config_obj.figshare_config()
        self.system_config = self.config_obj.system_config()
        self.api_endpoint = figshare_config["url"]
        self.api_token = figshare_config["token"]
        self.retries = int(figshare_config["retries"]) if figshare_config["retries"] is not None else 3
        self.retry_wait = int(figshare_config["retries_wait"]) if figshare_config["retries_wait"] is not None else 10
        self.logs = Log(config)
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
                while (not page_empty):
                    # page = 1
                    # page_size = 3
                    # total_articles = 5
                    # no_of_pages = math.ceil(total_articles / page_size)
                    # while (page <= no_of_pages):
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
                            break
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

        return article_data

    def article_loop(self, articles, page_size, page, article_data):
        no_of_article = 0
        for article in articles:
            if (article['published_date'] is not None or article['published_date'] != ''):
                no_of_article = no_of_article + 1
                print(f"Fetching article {no_of_article} of {page_size} on Page {page}. ID: {article['id']}")
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
                                print(f"Fetching article {article['id']} version {version['version']}.")
                                version_data = self.__get_article_metadata_by_version(version, article['id'])
                                metadata.append(version_data)
                        else:
                            version_data = self.private_article_for_data(private_url, article['id'])
                            if (version_data is not None and len(version_data) > 0):
                                metadata.append(version_data)
                        success = True
                        return metadata
                    else:
                        retries = self.retries_if_error(f"Public verion URL is not reachable. Retry {retries}",
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

                            self.total_all_articles_file_size += total_file_size

                            self.logs.write_log_in_file("info", f"{version_metadata} ")

                            error = f"{version_data['id']} - This item had a total embargo. The files are from version {version_data['version']}."
                            self.logs.write_log_in_file("info", f"{error}", True)
                            return version_data
                        else:
                            error = f"{version_data['id']} - This item’s curation_status was not 'approved'"
                            self.logs.write_log_in_file("info", f"{error}", True)
                            break
                    elif (get_response.status_code == 404):
                        res = get_response.json()
                        self.logs.write_log_in_file("info",
                                                    f"{article_id} - {res['message']}")
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
    If files doesn't found and size is > 0 in public API response then
    private api will be called for files.
    No. of tries implemented in while loop, loop will exit if API is not giving
    200 response after no. of tries defined in config file.
    If files > 0 then __download_files will be called
    """
    def __get_article_metadata_by_version(self, version, article_id):
        retries = 1
        success = False

        while not success and retries <= int(self.retries):
            try:
                if (version):
                    public_url = version['url']
                    get_response = requests.get(public_url)
                    if (get_response.status_code == 200):
                        version_data = get_response.json()
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
                        json_data = json.dumps(version_data).encode("utf-8")
                        version_md5 = hashlib.md5(json_data).hexdigest()

                        version_metadata = self.set_version_metadata(version_data, files, private_version_no, version_md5, total_file_size)
                        version_data['total_num_files'] = file_len
                        version_data['file_size_sum'] = total_file_size
                        version_data['version_md5'] = version_md5
                        if (error):
                            version_metadata['errors'] = []
                            version_metadata['errors'].append(error)

                        self.total_all_articles_file_size += total_file_size

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
                error = f"{version_data['id']} - This item’s curation_status was not 'approved'"
                self.logs.write_log_in_file("info", f"{error}", True)

        return {"files": files, "private_version_no": private_version_no, "file_len": file_len}

    """
    This function will download files and place them in directory, with version_metadata.
    """
    def __download_files(self, files, version_data, folder_name):
        delete_folder = False
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
                    filecontent = requests.get(file['download_url'], headers={'Authorization': 'token ' + self.api_token},
                                               allow_redirects=True,
                                               )
                    if (filecontent.status_code == 200):
                        file_no = file_no + 1
                        print(f"Downloaded file {file_no} for article {version_data['id']} - version {version_data['version']}")
                        open(file_name_with_path, 'wb').write(filecontent.content)
                        existing_file_hash = hashlib.md5(open(file_name_with_path, 'rb').read()).hexdigest()
                        compare_hash = file['supplied_md5']
                        if (compare_hash == ""):
                            compare_hash = file['computed_md5']

                        if (existing_file_hash != compare_hash):
                            self.logs.write_log_in_file("error",
                                                        f"{version_data['id']} - Hash didn't matched after downloading."
                                                        + f" Name {file['name']}", True)
                            delete_folder = True
                            break
                    else:
                        self.logs.write_log_in_file("error",
                                                    f"{version_data['id']} - File doesn't download. Status code {filecontent.status_code}."
                                                    + f" Name {file['name']}", True)
                        delete_folder = True
                        break

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
    Checking curation directory, if require files found copying all files to temp directory on root of the script
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
                # check author name with article id directory exists like 'Jeffrey_C_Oliver_7873476'
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
                                version_data["matched"] = True
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
                                                                 'total_files_size': version_data['file_size_sum']
                                                                 }

                                # article version data with curation info saved in logs.
                                self.logs.write_log_in_file("info", f"{version_data} ")

                                if "UAL_RDM" not in read_version_dirs:  # check if UAL_RDM dir not exists...
                                    self.logs.write_log_in_file("error",
                                                                f"{version_data['id']} - UAL_RDM directory missing in curation storage."
                                                                + "Path is {version_dir}", True)
                                    break
                                else:
                                    version_data = self.read_version_dirs_fun(read_version_dirs, version_dir, version_data)

        return version_data

    def read_version_dirs_fun(self, read_version_dirs, version_dir, version_data):
        deposit_agrement_file = False
        redata_deposit_review_file = False
        trello_file = False
        for dir in read_version_dirs:
            if dir not in self.exclude_dirs:
                if dir == "UAL_RDM":
                    ual_rdm_path = version_dir + "/" + dir
                    ual_dir = os.listdir(ual_rdm_path)
                    for ual_file in ual_dir:
                        if (ual_file.startswith("Deposit Agreement")
                                or ual_file.startswith("Deposit_Agreement")):
                            deposit_agrement_file = True

                        if (ual_file.startswith("ReDATA-DepositReview")):
                            redata_deposit_review_file = True

                        if (ual_file.endswith("Trello.pdf")):
                            trello_file = True

        version_data["deposit_agrement_file"] = deposit_agrement_file
        version_data["redata_deposit_review_file"] = redata_deposit_review_file
        version_data["trello_file"] = trello_file

        return version_data

    """
    Get size of files of the given directory path
    :param dir_path string  path of dir where file size require to calculate.
    :return size integer
    """
    def get_file_size_of_given_path(self, dir_path):
        size = 0
        for path, dirs, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(path, f)
                size += os.path.getsize(fp)

        return size

    """
    Compare the required space with available space
    :param required_space integer
    :return log error and terminate script if required_space greater.
    """
    def check_required_space(self, required_space):
        req_space = required_space * (1 + (int(self.system_config["additional_percentage_required"]) / 100))
        preservation_storage_location = self.preservation_storage_location
        memory = shutil.disk_usage(preservation_storage_location)
        available_space = memory.free
        if (req_space > available_space):
            self.logs.write_log_in_file('error', "There isn't enough space in storage path."
                                                 + f"Required space is {req_space} and available space is {available_space}.", True, True)

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

        # check preservation dir is reachable
        self.check_access_of_directries(preservation_storage_location, "preservation")

        article_files_path_exists = os.path.exists(article_folder_path)
        process_article = False
        delete_folder = False

        if (article_files_path_exists is True):
            get_files = os.listdir(article_folder_path)
            if (len(get_files) > 0):
                for file in files:
                    file_path = article_folder_path + "/" + str(file['id']) + "_" + file['name']
                    file_exists = os.path.exists(file_path)
                    compare_hash = file['supplied_md5']
                    if (compare_hash == ""):
                        compare_hash = file['computed_md5']

                    if (file_exists is True):
                        # checking md5 values to check existing file is same or not.
                        existing_file_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
                        if (existing_file_hash != compare_hash):
                            delete_folder = True
                            self.logs.write_log_in_file('error', f"{file_path} hash does not match.", True)
                        else:
                            self.logs.write_log_in_file('info', f"{file_path} hash matched, files already exists.", True)

                        process_article = False
                        break
                    else:
                        self.logs.write_log_in_file('error', f"{file_path} does not exist.", True)
                        delete_folder = True
                        process_article = False
                        break
            else:
                process_article = True

        else:
            process_article = True

        # delete directory if validation failed.
        if (delete_folder is True):
            self.delete_folder(preservation_storage_location + folder_path)

        return process_article

    """
    Save json data for each article in related directory
    :param version_data dictionary
    :param folder_name string
    """
    def __save_json_in_metadata(self, version_data, folder_name):
        version_no = "v" + str(version_data["version"]).zfill(2)
        json_folder_path = folder_name + "/" + version_no + "/METADATA"
        preservation_storage_location = self.preservation_storage_location
        complete_path = preservation_storage_location + json_folder_path
        check_path_exists = os.path.exists(complete_path)
        if (check_path_exists is False):
            os.makedirs(complete_path, exist_ok=True)
        # Remove extra indexes from version data before getting save in json file
        # these indexes created in code while fetching data from APIs for further processing
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
        if ("deposit_agrement_file" in version_data):
            del (version_data["deposit_agrement_file"])
        if ("trello_file" in version_data):
            del (version_data["trello_file"])

        json_data = json.dumps(version_data, indent=4)
        filename_path = complete_path + "/" + str(version_data['id']) + ".json"
        # Writing to json file
        with open(filename_path, "w") as outfile:
            outfile.write(json_data)

    """
    Copying UAL_RDM folder files to storage directory in related article version folder
    :param version_data dictionary
    :param folder_name string
    """
    def __copy_files_ual_rdm(self, version_data, folder_name):
        version_no = "v" + str(version_data["version"]).zfill(2)
        curation_storage_location = self.curation_storage_location
        # author_name = version_data['authors'][0]["url_name"]
        # curation_dir_name = curation_storage_location + author_name + "_" + str(version_data['id']) + "/" + version_no + "/UAL_RDM"
        # check_folder = os.path.exists(curation_dir_name)
        # check curation dir is reachable
        self.check_access_of_directries(curation_storage_location, "curation")

        preservation_storage_location = self.preservation_storage_location
        complete_folder_name = preservation_storage_location + folder_name + "/" + version_no + "/UAL_RDM"
        dirs = os.listdir(curation_storage_location)
        for dir in dirs:
            if (dir not in self.exclude_dirs):
                dir_array = dir.split("_")
                # check author name with article id directory exists like 'Jeffrey_C_Oliver_7873476'
                if (str(version_data['id']) in dir_array):
                    article_dir_in_curation = curation_storage_location + dir
                    # read author dir
                    read_dirs = os.listdir(article_dir_in_curation)
                    for dir in read_dirs:
                        if dir not in self.exclude_dirs:
                            if (dir == version_no):
                                curation_dir_name = article_dir_in_curation + "/" + dir + "/UAL_RDM"
                                # check preservation dir is reachable
                                self.check_access_of_directries(preservation_storage_location, "preservation")
                                try:
                                    check_path_exists = os.path.exists(complete_folder_name)
                                    if (check_path_exists is False):
                                        os.makedirs(complete_folder_name, exist_ok=True)
                                    # copying files to storage version folder
                                    shutil.copytree(curation_dir_name, complete_folder_name, dirs_exist_ok=True)
                                except Exception as e:
                                    self.logs.write_log_in_file('error', f"{e} - {complete_folder_name} err while coping file.", True)

    """
    Find matched articles from the fetched data and curation dir
    """
    def find_matched_articles(self, articles):
        article_data = {}
        for article in articles:
            if (articles[article] is not None):
                article_versions_list = articles[article]
                article_data[article] = []
                for version_data in article_versions_list:
                    # check curation folder for required files and setup data for further processing.
                    if (version_data is not None and len(version_data) > 0):
                        data = self.__check_curation_dir(version_data)
                        if (data["matched"] is True):
                            article_data[version_data['id']].append(data)

        return article_data

    """
    Check files are copyable or not
    """
    def __can_copy_files(self, version_data):
        if (version_data["deposit_agrement_file"] is False
                or version_data["redata_deposit_review_file"] is False
                or version_data["trello_file"] is False):
            self.logs.write_log_in_file("error", f"{version_data['id']} - UAL_RDM directory doesn't have required "
                                        + "files in curation storage.", True)
            copy_files = False
        else:
            copy_files = True

        return copy_files

    """
    Final process for matched articles.
    """
    def __final_process(self, check_files, copy_files, check_dir, version_data, folder_name, version_no):
        if (check_files is True and copy_files is True):
            # download all files and veriy hash with downloaded file.
            delete_now = self.__download_files(version_data['files'], version_data, folder_name)
            # check download process has error or not.
            if (delete_now is False):
                # copy curation UAL_RDM files in storage UAL_RDM folder for each version
                self.logs.write_log_in_file("info", "Copy curation UAL_RDM files in storage UAL_RDM folder for each version", True)
                self.__copy_files_ual_rdm(version_data, folder_name)
                # check and create empty directories for each version
                self.logs.write_log_in_file("info", "Check and create empty directories for each version", True)
                self.create_required_folders(version_data, folder_name)
                # save json in metadata folder for each version
                self.logs.write_log_in_file("info", "Save json in metadata folder for each version", True)
                self.__save_json_in_metadata(version_data, folder_name)
            else:
                # if download process has any error than delete complete folder
                self.logs.write_log_in_file("info", "If download process has any error than delete complete folder", True)
                self.delete_folder(check_dir)
        else:
            # call post process script function for each match item.
            value_post_process = self.post_process_script_function()
            if (value_post_process != 0):
                self.logs.write_log_in_file("error", f"{version_data['id']} {version_no}- post script error found.", True)

    """
    Called before articles processing.
    """
    def __initial_process(self, total_file_size):
        # get curation directory path
        curation_storage_location = self.curation_storage_location
        # get preservation directory path
        preservation_storage_location = self.preservation_storage_location
        # curation dir is reachable
        self.check_access_of_directries(curation_storage_location, "curation")

        # preservation dir is reachable
        self.check_access_of_directries(preservation_storage_location, "preservation")

        # check required space after Figshare API process, it will stop process if space is less.
        self.check_required_space(total_file_size)

        return curation_storage_location

    """
    Process all articles after fetching from API.
    """
    def process_articles(self, articles, total_file_size):
        curation_storage_location = self.__initial_process(total_file_size)
        article_data = self.find_matched_articles(articles)
        # calcualte space for given path.
        curation_folder_size = self.get_file_size_of_given_path(curation_storage_location)
        required_space = curation_folder_size + self.total_all_articles_file_size
        # check required space after curation process, it will stop process if space is less.
        self.check_required_space(required_space)

        for article in article_data:
            article_versions_list = articles[article]
            article_data[article] = []
            for version_data in article_versions_list:
                if version_data is not None or len(version_data) > 0:
                    print(f"Processing article {article} version {version_data['version']}")
                    version_no = "v" + str(version_data["version"]).zfill(2)
                    folder_name = str(version_data["id"]) + "_" + version_no + "_" \
                        + version_data['authors'][0]['url_name'] + "_" + version_data['version_md5']

                    if (version_data["matched"] is True):
                        # call pre process script function for each match item.
                        value_pre_process = self.pre_process_script_function()
                        if (value_pre_process == 0):
                            # check main folder exists in preservation storage.
                            preservation_storage_location = self.preservation_storage_location
                            check_dir = preservation_storage_location + folder_name
                            check_main_folder = os.path.exists(check_dir)
                            check_files = True
                            copy_files = True
                            self.logs.write_log_in_file("info", "Check folder already exists in preservation storage directory.", True)
                            if (check_main_folder is True):
                                get_dirs = os.listdir(check_dir)
                                if (len(get_dirs) > 0):
                                    check_files = self.__check_file_hash(version_data['files'], version_data, folder_name)
                                else:
                                    check_files = False
                                    # delete folder if validation fails
                                    self.delete_folder(check_dir)
                                    # call pre process script function for each match item.
                                    value_post_process = self.post_process_script_function()
                                    if (value_post_process != 0):
                                        self.logs.write_log_in_file("error", f"{version_data['id']} - post script error found.", True)
                                    break
                            # end check main folder exists in preservation storage.
                            # check require files exists in curation UAL_RDM folder
                            self.logs.write_log_in_file("info", "Check require files exists in curation UAL_RDM folder.", True)
                            copy_files = self.__can_copy_files(version_data)
                            self.__final_process(check_files, copy_files, check_dir, version_data, folder_name, version_no)
                        else:
                            # call post process script function for each match item.
                            value_post_process = self.post_process_script_function()
                            if (value_post_process != 0):
                                self.logs.write_log_in_file("error", f"{version_data['id']} {version_no}- post script error found.", True)

    """
    Preservation and Curation directory access check while processing.
    Retries also implemented.
    :param directory_path string
    :param process_name string
    """
    def check_access_of_directries(self, directory_path, process_name="preservation"):
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
                                                + f" not be reached or read.. Retry {retries}", 500, retries)
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
        if (ual_path_exists is False):
            # create UAL_RDM directory if not exist
            os.makedirs(ual_folder_name, exist_ok=True)

        # setup DATA directory
        data_folder_name = preservation_storage_location + folder_name + "/" + version_no + "/DATA"
        data_path_exists = os.path.exists(data_folder_name)
        if (data_path_exists is False):
            # create DATA directory if not exist
            os.makedirs(data_folder_name, exist_ok=True)

    """
    Preprocess script command function.
    """
    def pre_process_script_function(self):
        pre_process_script_command = self.system_config["pre_process_script_command"]
        if (pre_process_script_command != ""):
            print(f"Processing....{pre_process_script_command}")
        else:
            return 0

    """
    Postprocess script command function.
    """
    def post_process_script_function(self):
        post_process_script_command = self.system_config["post_process_script_command"]
        if (post_process_script_command != ""):
            print(f"Processing....{post_process_script_command}")
        else:
            return 0

    """
    Delete folder
    """
    def delete_folder(self, folder_path):
        check_exsits = os.path.exists(folder_path)
        if (check_exsits is True):
            shutil.rmtree(folder_path)
            self.logs.write_log_in_file("error", f"{folder_path} deleted due to failed validations.")

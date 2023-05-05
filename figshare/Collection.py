import json
import os
import requests
import hashlib
import re
from Log import Log
from Config import Config
from figshare.Article import Article
from figshare.Integration import Integration


class Collection:

    """
    Class constructor.
    Defined variables that will be used in whole class
    """
    def __init__(self, config) -> None:
        self.config_obj = Config(config)
        figshare_config = self.config_obj.figshare_config()
        self.system_config = self.config_obj.system_config()
        self.api_endpoint = figshare_config["url"]
        self.api_token = figshare_config["token"]
        self.retries = int(figshare_config["retries"]) if figshare_config["retries"] is not None else 3
        self.retry_wait = int(figshare_config["retries_wait"]) if figshare_config["retries_wait"] is not None else 10
        self.institution = int(figshare_config["institution"])
        self.logs = Log(config)
        self.errors = []
        self.article_obj = Article(config)
        self.preservation_storage_location = self.system_config["preservation_storage_location"]
        if self.preservation_storage_location[-1] != "/":
            self.preservation_storage_location = self.preservation_storage_location + "/"

    """
    API get request sent to '/collections'.
    No. of tries implemented in while loop, loop will exit if API
    is not giving 200 response after no. of tries defined in config file.
    Static variables implemented for pagination. page, page_size, no_of_pages.
    On successful response from above mentioned API, __get_collection_versions
    will be called with collection param.
    """
    def get_collections(self):
        collections_api_url = self.get_collection_api_url()
        retries = 1
        success = False
        collection_data = {}
        while not success and retries <= int(self.retries):
            try:
                # pagination implemented.
                page = 1
                page_size = 100
                page_empty = False
                self.logs.write_log_in_file("info", f"Page size is {page_size}.", True)
                while (not page_empty):
                    self.logs.write_log_in_file("info", f"Getting page {page} of collections. Total amount of pages not available.", True)
                    params = {'page': page, 'page_size': page_size, 'institution': self.institution}
                    get_response = requests.get(collections_api_url, params=params,
                                                timeout=self.retry_wait)
                    if (get_response.status_code == 200):
                        collections = get_response.json()
                        if (len(collections) == 0):
                            page_empty = True
                            self.logs.write_log_in_file("info", "Page of collections is empty.", True)
                            break

                        collection_data = self.collections_loop(collections, page_size, page, collection_data)
                        success = True
                    else:
                        success = False
                        retries = self.article_obj.retries_if_error(
                            f"API is not reachable. Retry {retries}", get_response.status_code, retries)
                        if (retries > self.retries):
                            break
                    page += 1

            except Exception as e:
                success = False
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if (retries > self.retries):
                    break

        return collection_data

    def collections_loop(self, collections, page_size, page, collection_data):
        no_of_col = 0
        for collection in collections:
            no_of_col = no_of_col + 1
            self.logs.write_log_in_file("info", f"Fetching collection {no_of_col} on page {page}. ID: {collection['id']}.", True)
            coll_versions = self.__get_collection_versions(collection)
            coll_articles = self.__get_collection_articles(collection)
            collection_data[collection['id']] = {"versions": coll_versions, "articles": coll_articles}

        return collection_data

    """
    This function will send request to fetch collection versions.
    :param collection object.
    On successful response from '/versions' API, __get_collection_metadata_by_version will
    be called with version and collection id param.
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response
    after no. of tries defined in config file.
    """
    def __get_collection_versions(self, collection):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if (collection):
                    public_url = collection['url']
                    version_url = public_url + "/versions"
                    get_response = requests.get(version_url, timeout=self.retry_wait)
                    if (get_response.status_code == 200):
                        versions = get_response.json()
                        metadata = []
                        if (len(versions) > 0):
                            for version in versions:
                                self.logs.write_log_in_file("info", f"Fetching collection {collection['id']} version {version['version']}.", True)
                                version_data = self.__get_collection_metadata_by_version(version, collection['id'])
                                metadata.append(version_data)
                            success = True
                            return metadata
                        else:
                            self.logs.write_log_in_file("info", f"{collection['id']} - Entity not found. It will be skipped during processing.")
                            break
                    else:
                        retries = self.article_obj.retries_if_error(
                            f"Public verion URL is not reachable. Retry {retries}", get_response.status_code, retries)
                        success = False
                        if (retries > self.retries):
                            break
            except Exception as e:
                success = False
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if (retries > self.retries):
                    break

    """
    Fetch collection metadata by version url.
    :param version object value.
    :param collection_id int value.
    On successful response from url API, metadata array will be setup for response.
    No. of tries implemented in while loop, loop will exit if API is not
    giving 200 response after no. of tries defined in config file.
    """
    def __get_collection_metadata_by_version(self, version, collection_id):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if (version):
                    public_url = version['url']
                    get_response = requests.get(public_url, timeout=self.retry_wait)
                    if (get_response.status_code == 200):
                        version_data = get_response.json()
                        version_metadata = version_data
                        self.logs.write_log_in_file("info", f"Collection id - {collection_id} - {version_metadata} ")
                        success = True
                        return version_data
                    else:
                        retries = self.article_obj.retries_if_error(
                            f"{collection_id} API not reachable. Retry {retries}", get_response.status_code, retries)
                        success = False
                        if (retries > self.retries):
                            break
            except Exception as e:
                success = False
                retries = self.article_obj.retries_if_error(f"{e}. Retry {retries}", get_response.status_code, retries)
                if (retries > self.retries):
                    break

    def __get_collection_articles(self, collection):
        """
        Function to fetch articles from collection API
        :param collection object
        :return articles object
        """
        coll_articles_api = self.get_article_api_url(collection)
        retries = 1
        success = False
        articles_list = []
        page_empty = False
        while not success and retries <= int(self.retries) and not page_empty:
            try:
                page = 1
                page_size = 100
                while (not page_empty):
                    self.logs.write_log_in_file("info", f"Fetching page {page} of collection articles. Collection ID: {collection['id']}.", True)
                    params = {'page': page, 'page_size': page_size}
                    get_response = requests.get(coll_articles_api, params=params, timeout=self.retry_wait)
                    if (get_response.status_code == 200):
                        articles_list_res = get_response.json()
                        if (len(articles_list_res) == 0):
                            page_empty = True
                            self.logs.write_log_in_file("info", f"Page of collection articles is empty. Collection ID: {collection['id']}.", True)
                            break
                        else:
                            articles_list.extend(articles_list_res)
                        success = True
                    else:
                        retries = self.article_obj.retries_if_error(
                            f"API is not reachable. Retry {retries}", get_response.status_code, retries)
                        success = False
                        if (retries > self.retries):
                            break
                    page += 1
                    if (page_empty is True):
                        success = False
                        break

            except Exception as e:
                success = False
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if (retries > self.retries):
                    break

        return articles_list

    def get_article_api_url(self, collection):
        api_url = f"collections/{collection['id']}/articles"
        coll_articles_api = self.api_endpoint + api_url
        if self.api_endpoint[-1] != "/":
            coll_articles_api = f"{self.api_endpoint}/{api_url}"

        return coll_articles_api

    """
    Function to process collections and its articles with collection versions.
    :param collections object
    """
    def process_collections(self, collections):
        self.logs.write_log_in_file("info", "Processing collections.", True)
        for collection in collections:
            data = collections[collection]
            articles = data["articles"]
            versions = data['versions']
            for version in versions:
                json_data = json.dumps(version).encode("utf-8")
                version_md5 = hashlib.md5(json_data).hexdigest()
                version_no = f"v{str(version['version']).zfill(2)}"
                author_name = re.sub("[^A-Za-z0-9]", "_", version['authors'][0]['full_name'])
                folder_name = str(collection) + "_" + version_no + "_" + author_name + "_" + version_md5 + "/" + version_no + "/METADATA"
                version["articles"] = articles
                self.logs.write_log_in_file("info", f"Processing collection {collection} version {version['version']}.", True)
                self.__save_json_in_metadata(collection, version, folder_name)
                collection_preservation_path = self.preservation_storage_location + os.path.basename(os.path.dirname(os.path.dirname(folder_name)))
                value_post_process = Integration.post_process_script_function(self, "Collection", collection_preservation_path)
                if (value_post_process != 0):
                    self.logs.write_log_in_file("error", f"collection {collection} - post-processing script failed.", True)

    """
    Save json data for each collection version in related directory
    :param version_data dictionary
    :param folder_name string
    """
    def __save_json_in_metadata(self, collection_id, version_data, folder_name):
        preservation_storage_location = self.preservation_storage_location

        self.article_obj.check_access_of_directories(preservation_storage_location, "preservation")

        complete_path = preservation_storage_location + folder_name
        check_path_exists = os.path.exists(complete_path)
        if (check_path_exists is False):
            os.makedirs(complete_path, exist_ok=True)
            json_data = json.dumps(version_data, indent=4)
            filename_path = complete_path + "/" + str(collection_id) + ".json"
            # Writing to json file
            self.logs.write_log_in_file("info", "Saving collection data in json.", True)
            with open(filename_path, "w") as outfile:
                outfile.write(json_data)
        else:
            storage_collection_version_dir = os.listdir(complete_path)
            file_name = f"{str(collection_id)}.json"
            if (len(storage_collection_version_dir) == 0 or file_name not in storage_collection_version_dir):
                self.logs.write_log_in_file("info", f"{complete_path} path already exists but missing {file_name} file.")

    def get_collection_api_url(self):
        collections_api_url = self.api_endpoint + '/collections'
        if self.api_endpoint[-1] == "/":
            collections_api_url = self.api_endpoint + "collections"

        return collections_api_url

    def fetch_by_collection_id(self):
        collection_id = 2830067
        success = False
        retries = 1
        while not success and retries <= int(self.retries):
            try:
                collection_api_url = self.get_collection_api_url()
                collection_api_url = collection_api_url + '/' + str(collection_id)
                get_response = requests.get(collection_api_url, timeout=self.retry_wait)
                if (get_response.status_code == 200):
                    collection = get_response.json()
                    coll_versions = self.__get_collection_versions(collection)
                    self.logs.write_log_in_file("info", f"{coll_versions}", True)

            except Exception as e:
                success = False
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if (retries > self.retries):
                    break

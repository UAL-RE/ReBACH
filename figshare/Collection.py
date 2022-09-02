import json
import math
import os
import sys
import time
import requests
from Log import Log
from Config import Config
import hashlib
from figshare.Article import Article

class Collection:

    """
    Class constructor.
    Defined variables that will be used in whole class
    """
    def __init__(self) -> None:
        self.config_obj = Config()
        figshare_config = self.config_obj.figshare_config()
        self.system_config = self.config_obj.system_config()
        self.api_endpoint = figshare_config["url"]
        self.api_token = figshare_config["token"]
        self.retries = int(figshare_config["retries"]) if figshare_config["retries"] != None else 3
        self.retry_wait = int(figshare_config["retries_wait"]) if figshare_config["retries_wait"] != None else 10
        self.logs = Log()
        self.errors = []
        self.article_obj = Article()

    """
    API get request sent to '/collections'.
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response after no. of tries defined in config file. 
    Static variables implemented for pagination. page, page_size, no_of_pages.
    On successful response from above mentioned API, __get_collection_versions will be called with collection param. 
    """
    def get_collections(self):
        collections_api_url = self.api_endpoint + '/collections' if self.api_endpoint[-1] == "/" else self.api_endpoint + "/collections"
        retries = 1
        success = False
        collection_data = {}
        while not success and retries <= int(self.retries):
            try:
                # pagination implemented. 
                # page = 1
                # page_size = 3
                # page_empty = False
                # while(not page_empty):
                page = 1
                page_size = 3
                total_articles = 5
                no_of_pages = math.ceil(total_articles / page_size)
                while(page <= no_of_pages):
                    print(f"page--{str(page)}" )
                    params = {'page': page, 'page_size': page_size}
                    get_response = requests.get(collections_api_url,
                        params=params
                    )
                    if (get_response.status_code == 200):
                        collections = get_response.json()
                        if(len(collections) == 0):
                            page_empty = True

                        for collection in collections:
                            coll_versions = self.__get_collection_versions(collection)
                            coll_articles = self.__get_collection_articles(collection)
                            collection_data[collection['id']] = {"versions": coll_versions, "articles": coll_articles}
                        
                        success = True
                    else:    
                        retries = self.article_obj.retries_if_error(f"API is not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
                    page += 1

            except Exception as e:
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if(retries > self.retries):
                    break

        return collection_data                
        

    """
    This function will send request to fetch collection versions. 
    :param collection object. 
    On successful response from '/versions' API, __get_collection_metadata_by_version will be called with version and collection id param. 
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response after no. of tries defined in config file. 
    """
    def __get_collection_versions(self, collection):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if(collection):
                    print(collection['id'])
                    public_url = collection['url']
                    version_url = public_url + "/versions"
                    get_response = requests.get(version_url)
                    if (get_response.status_code == 200):
                        versions = get_response.json()
                        metadata = []
                        if(len(versions) > 0):
                            for version in versions:
                                version_data = self.__get_collection_metadata_by_version(version, collection['id'])
                                metadata.append(version_data)
                            success = True
                            return metadata
                        else:
                            self.logs.write_log_in_file("info", f"{collection['id']} - Entity not found")
                            break
                    else:
                        retries = self.article_obj.retries_if_error(f"Public verion URL is not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if(retries > self.retries):
                    break

    """
    Fetch collection metadata by version url.
    :param version object value. 
    :param collection_id int value. 
    On successful response from url API, metadata array will be setup for response. 
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response after no. of tries defined in config file. 
    """
    def __get_collection_metadata_by_version(self, version, collection_id):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if(version):
                    public_url = version['url']
                    get_response = requests.get(public_url)
                    if (get_response.status_code == 200):
                        version_data = get_response.json()

                        version_metadata = version_data
                        
                        self.logs.write_log_in_file("info", f"{version_metadata} ")

                        return version_data
                    else:
                        retries = self.article_obj.retries_if_error(f"{collection_id} API not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.article_obj.retries_if_error(f"{e}. Retry {retries}", get_response.status_code, retries)
                if(retries > self.retries):
                    break

    def __get_collection_articles(self, collection):
        """
        Function to fetch articles from collection API
        :param collection object
        :return articles object
        """
        page = 1
        page_size = 100
        page_empty = False
        api_url = f"collections/{collection['id']}/articles"
        coll_articles_api = self.api_endpoint + api_url if self.api_endpoint[-1] == "/" else self.api_endpoint + f"/{api_url}"
        retries = 1
        success = False
        articles_list = []
        while not success and retries <= int(self.retries):
            try:
                while(not page_empty):
                    params = {'page': page, 'page_size': page_size}
                    get_response = requests.get(coll_articles_api, params=params)
                    if (get_response.status_code == 200):
                        articles = get_response.json()
                        if(len(articles) == 0):
                            page_empty = True
                            break
                        
                        articles_list = articles
                        
                        success = True
                    else:    
                        retries = self.article_obj.retries_if_error(f"API is not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
                    page += 1
            except Exception as e:
                retries = self.article_obj.retries_if_error(e, 500, retries)
                if(retries > self.retries):
                    break
        
        return articles_list

    """
    Function to process collections and it's articles with collection versions.
    :param collections object
    """
    def process_collections(self, collections):
        storage_folder = self.system_config["staging_storage_location"]
        existing_space = self.article_obj.get_file_size_of_given_path(storage_folder)
        self.article_obj.check_required_space(existing_space)

        for collection in collections:
            
            data = collections[collection]
            articles = data["articles"]
            versions = data['versions']
            for version in versions:
                json_data = json.dumps(version).encode("utf-8")
                version_md5 = hashlib.md5(json_data).hexdigest()
                version_no = f"v{str(version['version']).zfill(2)}" 
                folder_name = str(collection) + "_" + version_no + "_" + version_md5 + "/" + version_no + "/METADATA"
                version["articles"] = articles
                self.__save_json_in_metadata(collection, version, folder_name)

    
    """
    Save json data for each collection version in related directory
    :param version_data dictionary
    :param folder_name string
    """
    def __save_json_in_metadata(self, collection_id, version_data, folder_name):
        staging_storage_location = self.system_config["staging_storage_location"]
        complete_path = staging_storage_location + folder_name
        check_path_exists = os.path.exists(complete_path)
        if(check_path_exists == False):
            os.makedirs(complete_path, exist_ok=True)
            json_data = json.dumps(version_data, indent=4)
            filename_path = complete_path + "/" + str(collection_id) + ".json"
            # Writing to json file
            with open(filename_path, "w") as outfile:
                outfile.write(json_data)
        else:
            storage_collection_version_dir = os.listdir(complete_path)
            file_name = f"{str(collection_id)}.json"
            if(len(storage_collection_version_dir) == 0 or file_name not in storage_collection_version_dir):
                self.logs.write_log_in_file("info", f"{complete_path} path already exists but missing {file_name} file.")


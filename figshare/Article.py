import json
import math
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
    def __init__(self):
        self.config_obj = Config()
        figshare_config = self.config_obj.figshare_config()
        self.system_config = self.config_obj.system_config()
        self.api_endpoint = figshare_config["url"]
        self.api_token = figshare_config["token"]
        self.retries = int(figshare_config["retries"]) if figshare_config["retries"] != None else 3
        self.retry_wait = int(figshare_config["retries_wait"]) if figshare_config["retries_wait"] != None else 10
        self.logs = Log()
        self.errors = []
        self.exclude_dirs = [".DS_Store"]

    """
    This function is sending requests to 'account/institution/articles api.
    Static params given for pagination as page, page_size, no_of_pages.
    On successful response from above mentioned API, __get_article_versions will be called with article param. 
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response after no. of tries defined in config file. 
    """
    def get_articles(self):
        articles_api = self.api_endpoint + 'account/institution/articles' if self.api_endpoint[-1] == "/" else self.api_endpoint + "/account/institution/articles"
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                # pagination implemented. 
                page = 1
                page_size = 3
                total_articles = 5
                no_of_pages = math.ceil(total_articles / page_size)
                while(page <= no_of_pages):
                    params = {'page': page, 'page_size': page_size}
                    get_response = requests.get(articles_api,
                    headers={'Authorization': 'token '+self.api_token},
                    params=params
                    )
                    if (get_response.status_code == 200):
                        articles = get_response.json()
                        if(len(articles) == 0):
                            self.logs.write_log_in_file("info", f"API don't have more articles.", True, True)

                        article_data = []
                        for article in articles:
                            if(article['published_date'] != None or article['published_date'] != ''):
                                article_data.append({str(article['id']): self.__get_article_versions(article)})
                        
                        success = True
                        # return article_data
                    else:    
                        retries = self.retries_if_error(f"API is not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
                    page += 1
                    
            except Exception as e:
                retries = self.retries_if_error(e, 500, retries)
                if(retries > self.retries):
                    break
                

    """
    This function will send request to fetch article versions. 
    :param article object. 
    On successful response from '/versions' API, __get_article_metadata_by_version will be called with version param. 
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response after no. of tries defined in config file. 
    """
    def __get_article_versions(self, article):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if(article):
                    print(article['id'])
                    public_url = article['url_public_api']
                    version_url = public_url + "/versions"
                    get_response = requests.get(version_url)
                    if (get_response.status_code == 200):
                        versions = get_response.json()
                        metadata = []
                        if(len(versions) > 0):
                            for version in versions:
                                version_data = self.__get_article_metadata_by_version(version, article['id'])
                                metadata.append(version_data)
                            success = True
                            return metadata
                        else:
                            self.logs.write_log_in_file("info", f"{article['id']} - Entity not found: ArticleVersion")
                            break
                    else:
                        retries = self.retries_if_error(f"Public verion URL is not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.retries_if_error(e, 500, retries)
                if(retries > self.retries):
                    break

    """
    Fetch article metadata by version url.
    :param version object value. 
    :param article_id int value. 
    On successful response from url_public_api API, metadata array will be setup for response. 
    If files doesn't found and size is > 0 in public API response then private api will be called for files.
    No. of tries implemented in while loop, loop will exit if API is not giving 200 response after no. of tries defined in config file. 
    If files > 0 then __download_files will be called 
    """
    def __get_article_metadata_by_version(self, version, article_id):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if(version):
                    public_url = version['url']
                    get_response = requests.get(public_url)
                    if (get_response.status_code == 200):
                        version_data = get_response.json()
                        total_file_size = version_data['size']
                        files = []
                        error = ""
                        private_version_no = 0
                        if(total_file_size > 0 and 'files' not in version_data):
                            get_response = requests.get(version_data['url_private_api'], headers={'Authorization': 'token '+self.api_token})
                            file_len = 0
                            if (get_response.status_code == 200):
                                version_data_private = get_response.json()
                                # checking curation_status from article's private api
                                if (version_data_private['curation_status'] == "approved"):
                                    file_len = len(version_data_private['files'])
                                    files = version_data_private['files']
                                    private_version_no = version_data_private['version']
                                    error = f"{version_data['id']} - This item had a file embargo. The files are from version {str(private_version_no)}."
                                    self.logs.write_log_in_file("info", f"{error}", True)
                                else:
                                    error = f"{version_data['id']} - This item’s curation_status was not 'approved'"
                                    self.logs.write_log_in_file("info", f"{error}", True)

                        else:    
                            file_len = len(version_data['files'])
                            files = version_data['files']
                        # item_subtype conditions
                        sub_type = ''
                        if(version_data['has_linked_file']):
                            sub_type = 'linked'
                        elif(version_data['is_metadata_record']):
                            sub_type = 'metadata'
                        else:
                            sub_type = 'regular'
                        
                        version_md5 = ''
                        json_data = json.dumps(version_data).encode("utf-8")
                        version_md5 = hashlib.md5(json_data).hexdigest()

                        version_metadata = {'article_id': article_id, 
                        'metadata': {
                            'item_type': 'article', 'item_subtype': sub_type,'id': version_data['id'], 'version': version['version'], 'first_author': version_data['authors'][0], 'files': files, 
                            'total_num_files': file_len, 'file_size_sum': total_file_size, 'public_url': version_data['url_public_api'],'private_version_no': private_version_no, 'md5': version_md5
                            }
                        }
                        if(error): 
                            version_metadata['errors'] = []
                            version_metadata['errors'].append(error)
                        
                        version_no = "v" + str(version_data["version"]).zfill(2)
                        #folder name to store data in it.
                        folder_name = str(version_data["id"]) + "_" + version_no + "_" + version_data['authors'][0]['url_name'] + "_" + version_md5

                        if(file_len > 0):
                            required_space = total_file_size
                            self.__check_required_space(required_space, version_data["id"])
                            self.__check_curation_dir(version_data)
                            check_files = self.__check_file_hash(files, version_data, folder_name)
                            if(check_files == True):
                                self.__download_files(files, version_data, folder_name)
                        
                        # save json in metadata folder for each version
                        self.__save_json_in_metadata(version_data, folder_name)

                        # copy curation UAL_RDM files in storage UAL_RDM folder for each version
                        self.__copy_files_ual_rdm(version_data, folder_name)

                        self.logs.write_log_in_file("info", f"{version_metadata} ")

                        return version_metadata
                    else:
                        retries = self.retries_if_error(f"{article_id} API not reachable. Retry {retries}", get_response.status_code, retries)
                        if(retries > self.retries):
                            break
            except requests.exceptions.RequestException as e:
                retries = self.retries_if_error(f"{e}. Retry {retries}", get_response.status_code, retries)
                if(retries > self.retries):
                    break


    """
    This function will download files and place them in directory, with version_metadata.
    """
    def __download_files(self, files, version_data, folder_name):
        if(len(files) > 0):
            for file in files:
                if(file['is_link_only'] == False):
                    version_no = "v" + str(version_data["version"]).zfill(2)
                    # first_author_name = version_data["authors"][0]['url_name']
                    article_files_folder =  folder_name + "/" + version_no + "/DATA"
                    staging_storage_location = self.system_config["staging_storage_location"]
                    article_folder_path = staging_storage_location + article_files_folder
                    article_files_path_exists = os.path.exists(article_folder_path)
                    if(article_files_path_exists == False):
                        os.makedirs(article_folder_path, exist_ok=True)
                    
                    file_name_with_path = article_folder_path + "/" + str(file['id']) + "_" + file['name']   
                    filecontent = requests.get(file['download_url'], allow_redirects=True)
                    if(filecontent.status_code == 200):
                        open(file_name_with_path, 'wb').write(filecontent.content)

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
        curation_storage_location = self.system_config["curation_storage_location"]
        dirs = os.listdir(curation_storage_location)
        version_no = "v" + str(version_data["version"]).zfill(2)
        deposit_agrement_file = False
        redata_deposit_review_file = False
        
        for dir in dirs:
            if(dir not in self.exclude_dirs):
                author_name = version_data['authors'][0]["url_name"]
                
                check_dir_name = author_name + "_" + str(version_data['id'])
                # check auther name with article id directory exists like 'Jeffrey_C_Oliver_7873476'
                if(check_dir_name == dir):
                    article_dir_in_curation = curation_storage_location + dir 
                    read_dirs = os.listdir(article_dir_in_curation) # read auther dir

                    for dir in read_dirs:
                        if dir not in self.exclude_dirs:
                            if (dir == version_no):
                                version_dir = article_dir_in_curation + "/" + dir 
                                read_version_dirs = os.listdir(version_dir) # read version dir
                                
                                if "UAL_RDM" not in read_version_dirs: # check if UAL_RDM dir not exists...
                                    self.logs.write_log_in_file("error", f"{version_data['id']} - UAL_RDM directory missing in curation storage. Path is {version_dir}", True)
                                    break
                                else:
                                    for dir in read_version_dirs:
                                        if dir not in self.exclude_dirs:
                                            if dir == "UAL_RDM":
                                                ual_rdm_path = version_dir + "/" + dir
                                                ual_dir = os.listdir(ual_rdm_path)
                                                
                                                for ual_file in ual_dir:
                                                    if (ual_file == "Deposit Agreement.pdf" or ual_file == "Deposit_Agreement.pdf"):
                                                        deposit_agrement_file = True

                                                    if (ual_file.startswith("ReDATA-DepositReview")):
                                                        redata_deposit_review_file = True
                                                    
                                                    
                                    if(deposit_agrement_file == False or redata_deposit_review_file == False):
                                        self.logs.write_log_in_file("error", f"{version_data['id']} - UAL_RDM directory don't have required files in curation storage. Path is {ual_rdm_path}", True)
                                        break
                                    else:
                                        #Check temp path exits, if not then create directory
                                        temp_path = "./temp"
                                        temp_path_exists = os.path.exists(temp_path)
                                        if(temp_path_exists == False):
                                            os.makedirs(temp_path, exist_ok=True)
                                        
                                        temp_ual_path = temp_path + "/" + "temp_" + str(version_data['id']) + "_" + version_no
                                        temp_ual_path_exists = os.path.exists(temp_ual_path)
                                        if(temp_ual_path_exists == False):
                                            os.makedirs(temp_ual_path, exist_ok=True)

                                        ual_dir = version_dir + "/" + "UAL_RDM/"
                                        shutil.copytree(ual_dir, temp_ual_path, dirs_exist_ok=True)

                                        temp_ual_size = self.__get_file_size_of_given_path(temp_ual_path)
                                        required_space = temp_ual_size + version_data['size']
                                        self.__check_required_space(required_space, version_data['id'])


    """
    Get size of files of the given directory path
    :param dir_path string  path of dir where file size require to calculate.
    :return size integer 
    """   
    def __get_file_size_of_given_path(self, dir_path):
        size = 0
        for path, dirs, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(path, f)
                size += os.path.getsize(fp)
        
        return size
                                        

    """
    Compare the required space with available space 
    :param required_space integer
    :param article_id integer
    :return log error and terminate script if required_space greater.
    """
    def __check_required_space(self, required_space, article_id):
        req_space = required_space * int(self.system_config["additional_percentage_required"])
        staging_storage_location = self.system_config["staging_storage_location"]
        memory = shutil.disk_usage(staging_storage_location)
        available_space = memory.free
        if(req_space > available_space):
            self.logs.write_log_in_file('error', f"{article_id} - There isn't enough space in storage path.", True, True)

    
    """
    Checking file hash 
    :param files dictionary
    :param version_data dictionary
    :param folder_path string
    :return boolean
    """
    def __check_file_hash(self, files, version_data, folder_path):
        version_no = "v" + str(version_data["version"]).zfill(2)
        article_files_folder =  folder_path + "/" + version_no + "/DATA"
        staging_storage_location = self.system_config["staging_storage_location"]
        article_folder_path = staging_storage_location + article_files_folder
        article_files_path_exists = os.path.exists(article_folder_path)
        process_article = False
        if(article_files_path_exists == True):
            get_files = os.listdir(article_folder_path)
            if(len(get_files) > 0):
                for file in files:
                    file_path = article_folder_path + "/" + str(file['id']) + "_" + file['name']
                    file_exists = os.path.exists(file_path)
                    compare_hash = file['supplied_md5']
                    if(compare_hash == ""):
                        compare_hash = file['computed_md5']
                    
                    if(file_exists == True):
                        existing_file_hash = hashlib.md5(open(file_path,'rb').read()).hexdigest()
                        if(existing_file_hash != compare_hash):
                            process_article = False
                            self.logs.write_log_in_file('error', f"{file_path} hash does not match.", True)
                            break
                    else:
                        self.logs.write_log_in_file('error', f"{file_path} does not exist.", True)
                        process_article = False
                        break
            else:
                process_article = True
            
        else:
            process_article = True
        
        return process_article


    """
    Save json data for each article in related directory
    :param version_data dictionary
    :param folder_name string
    """
    def __save_json_in_metadata(self, version_data, folder_name):
        version_no = "v" + str(version_data["version"]).zfill(2)
        json_folder_path = folder_name + "/" + version_no + "/METADATA"
        staging_storage_location = self.system_config["staging_storage_location"]
        complete_path = staging_storage_location + json_folder_path
        check_path_exists = os.path.exists(complete_path)
        if(check_path_exists == False):
            os.makedirs(complete_path, exist_ok=True)
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
        temp_path = "./temp"
        temp_ual_path = temp_path + "/" + "temp_" + str(version_data['id']) + "_" + version_no
        comp_temp_path = os.path.abspath(temp_ual_path)
        check_temp_folder = os.path.exists(comp_temp_path)
        
        if(check_temp_folder == True):
            staging_storage_location = self.system_config["staging_storage_location"]
            complete_folder_name = staging_storage_location + folder_name + "/" + version_no + "/UAL_RDM"
            
            try:
                check_path_exists = os.path.exists(complete_folder_name)
                if(check_path_exists == False):
                    os.makedirs(complete_folder_name, exist_ok=True)
                #copying files to storage version folder 
                shutil.copytree(temp_ual_path, complete_folder_name, dirs_exist_ok=True)
                #delete temp folder of related version
                shutil.rmtree(temp_ual_path)
            except Exception as e:
                self.logs.write_log_in_file('error', f"{e} - {complete_folder_name} err while coping file.", True)
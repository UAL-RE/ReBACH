from asyncio import exceptions
from ensurepip import version
import sys
import time
import requests
from Log import Log
from Config import Config

class Article:
    api_endpoint = ""
    api_token = ""

    # class constructor
    def __init__(self):
        self.config_obj = Config()
        figshare_config = self.config_obj.figshare_config()
        system_config = self.config_obj.system_config()
        self.api_endpoint = figshare_config["url"]
        self.api_token = figshare_config["token"]
        self.retries = figshare_config["retries"] if figshare_config["retries"] != None else 3
        self.retry_wait = int(figshare_config["retries_wait"]) if figshare_config["retries_wait"] != None else 10
        self.logs = Log()
        self.errors = []

    # this function send request to fetch articles from api
    def get_articles(self):
        articles_api = self.api_endpoint + 'account/institution/articles' if self.api_endpoint[-1] == "/" else self.api_endpoint + "/account/institution/articles"
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                print(time.asctime())
                params = {'page': 1, 'page_size': 5}
                get_response = requests.get(articles_api,
                headers={'Authorization': 'token '+self.api_token},
                # params=params
                )
                if (get_response.status_code == 200):
                    articles = get_response.json()
                    article_data = []
                    for article in articles:
                        article_data.append({str(article['id']): self.__get_article_versions(article)})
                    
                    success = True
                    print(time.asctime())
                    # return article_data
                else:    
                    retries = self.__retries_if_error(f"API is not reachable. retrie {retries}", get_response.status_code, retries)
                    
            except Exception as e:
                retries = self.__retries_if_error(e, 500, retries)
                

    # Private function - This function will send request to fetch article versions
    def __get_article_versions(self, article):
        retries = 1
        success = False
        while not success and retries <= int(self.retries):
            try:
                if(article):
                    public_url = article['url_public_api'] + "sd"
                    get_response = requests.get(public_url)
                    if (get_response.status_code == 200):
                        version_url = public_url + "/versions"
                        get_response = requests.get(version_url)
                        versions = get_response.json()
                        metadata = []
                        for version in versions:
                            version_data = self.__get_article_metadata_by_version(version, article['id'])
                            metadata.append(version_data)
                        return metadata
                    else:
                        retries = self.__retries_if_error(f"Public URL is not reachable. retrie {retries}", get_response.status_code, retries)
            except requests.exceptions.RequestException as e:
                retries = self.__retries_if_error(e, 500, retries)

    # Private function - Fetch article metadata by version url.
    def __get_article_metadata_by_version(self, version, article_id):
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
                            if (version_data_private['curation_status'] == "approved"):
                                file_len = len(version_data_private['files'])
                                files = version_data_private['files']
                                private_version_no = version_data_private['version']
                                error = f"This item had a file embargo. The files are from version {str(private_version_no)}."
                            else:
                                error = "This item’s curation_status was not approved"

                    else:    
                        file_len = len(version_data['files'])
                        files = version_data['files']

                    version_metadata = {'article_id': article_id, 
                    'metadata': {
                        'id': version_data['id'], 'version': version['version'], 'first_author': version_data['authors'][0], 'files': files, 
                        'total_num_files': file_len, 'file_size_sum': total_file_size, 'public_url': version_data['url_public_api'],'private_version_no': private_version_no
                        }
                    }
                    self.__download_files(files)
                    if(error): 
                        version_metadata['errors'] = []
                        version_metadata['errors'].append(error)
                    return version_metadata
                else:
                    self.logs.write_log_in_file("warning", f"{article_id} - Status code {get_response.status_code}")
        except requests.exceptions.RequestException as e:
            self.logs.write_log_in_file("error", e)


    # Download files if exists
    def __download_files(self, files):
        if(len(files) > 0):
            for file in files:
                print(f"Start file downloading....{time.asctime()}")
                print(f"{file['download_url']}")
                print(f"End file downloading....{time.asctime()}")

    def __retries_if_error(self, msg, status_code, retries):
        self.logs.show_log_in_terminal("error", f"{msg} - Status code {status_code}")
        wait = self.retry_wait
        print ('Error! Waiting %s secs and re-trying...' % wait)
        # sys.stdout.flush()
        time.sleep(wait)
        retries = int(retries) + 1
        return retries
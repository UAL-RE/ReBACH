from asyncio import exceptions
from ensurepip import version
import sys
import time
from dotenv import load_dotenv
import os
import requests
from Log import Log
from LogToFile import LogToFile

class Article:
    api_endpoint = ""
    api_token = ""

    # class constructor
    def __init__(self):
        self.api_endpoint = os.getenv("FIGSHARE_ENDPOINT")
        self.api_token = os.getenv("FIGSHARE_TOKEN")
        self.retries = os.getenv("FIGSHARE_RETRIES") if os.getenv("FIGSHARE_RETRIES") != None else 3
        self.retry_wait = os.getenv("FIGSHARE_RETRY_WAIT") if os.getenv("FIGSHARE_RETRY_WAIT") != None else 10
        self.logs = Log()
        self.errors = []

    # this function send request to fetch articles from api
    def get_articles(self):
        articles_api = self.api_endpoint + 'account/institution/articles' if self.api_endpoint[-1] == "/" else self.api_endpoint + "/account/institution/articles"
        try:
            retries = 1
            success = False
            while not success and retries <= int(self.retries):
                print(time.asctime())
                params = {'page': 1, 'page_size': 5}
                get_response = requests.get(articles_api,
                headers={'Authorization': 'token '+self.api_token},
                params=params
                )
                if (get_response.status_code == 200):
                    articles = get_response.json()
                    article_data = []
                    for article in articles:
                        article_data.append({str(article['id']): self.__get_article_versions(article)})
                    
                    # logToFile = Log()
                    # logToFile.show_log_in_terminal("info", article_data)
                    success = True
                    print(time.asctime())
                    return article_data
                else:    
                    self.logs.show_log_in_terminal("error", f"Status code {get_response.status_code}")
                    raise
        except Exception as e:
            self.logs.show_log_in_terminal("error", e)
            wait = self.retry_wait
            print ('Error! Waiting %s secs and re-trying...' % wait)
            sys.stdout.flush()
            time.sleep(wait)
            retries += 1
            print (retries)

    # Private function - This function will send request to fetch article versions
    def __get_article_versions(self, article):
        try:
            if(article):
                public_url = article['url_public_api']
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
                    self.logs.show_log_in_terminal("warning", f"{article['id']} - status code {get_response.status_code}")
        except requests.exceptions.RequestException as e:
            self.logs.write_log_in_file("error", e)
    

    # Private function - Fetch article metadata by version url.
    def __get_article_metadata_by_version(self, version, article_id):
        try:
            if(version):
                public_url = version['url']
                get_response = requests.get(public_url)
                if (get_response.status_code == 200):
                    # get_response = requests.get(public_url)
                    version_data = get_response.json()
                    total_file_size = version_data['size']
                    files = []
                    if(total_file_size > 0 and 'files' not in version_data):
                        get_response = requests.get(version_data['url_private_api'], headers={'Authorization': 'token '+self.api_token})
                        file_len = 0
                        if (get_response.status_code == 200):
                            version_data = get_response.json()
                            file_len = len(version_data['files'])
                            files = version_data['files'] if file_len > 0 else "Files are missing."
                    else:    
                        file_len = len(version_data['files'])
                        files = version_data['files'] if file_len > 0 else "Files are missing."

                    # errors = self.__get_errors(version_data)

                    version_metadata = {'article_id': article_id, 
                    'metadata': {
                        'id': version_data['id'], 'version': version['version'], 'first_author': version_data['authors'][0], 'files': files, 'total_num_files': file_len, 'file_size_sum': total_file_size, 'public_url': version_data['url_public_api']
                        }}
                    # self.logs.write_log_in_file("info", version_metadata)
                    return version_metadata
                else:
                    self.logs.write_log_in_file("warning", f"{article_id} - Status code {get_response.status_code}")
        except requests.exceptions.RequestException as e:
            self.logs.write_log_in_file("error", e)


    # def __get_errors(self, version_data):
    #     errors = {}
    #     if('files' not in version_data or version_data['files'] == ''):

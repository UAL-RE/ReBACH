from dotenv import load_dotenv
import os
from Log import Log
from figshare.Article import Article
from time import asctime
from Config import Config

load_dotenv()

def main():
    log = Log()
    # Check .env file exist.
    file_exists = os.path.exists(".env.ini")

    if(file_exists == False):
        print(asctime() + ":ERROR: Log - " + "Please setup .env.ini file from .env.sample.ini file.")
        exit()

    config_obj = Config()
    figshare_config = config_obj.figshare_config()
    system_config = config_obj.system_config()

    figshare_api_url = figshare_config["url"]
    log_location = system_config["logs_location"]
    staging_storage_location = system_config["staging_storage_location"]
    figshare_api_token = figshare_config["token"]
    
    # Check required env variables exist.
    if(log_location == ""):
        print(asctime() + ":ERROR: Log - " + "Logs file path missing in .env file.")
        exit()

    if(figshare_api_url == "" or figshare_api_token == ""):
        log.write_log_in_file('error', "Figshare API URL and Token is required.", True)
    
    if(staging_storage_location == ""):
        log.write_log_in_file('error', "Staging storage location path is required.", True)

    #Check logs path exits, if not then create directory
    logs_path_exists = os.path.exists(log_location)
    if(logs_path_exists == False):
        os.mkdir(log_location, 777)

    #Check storage path exits, if not then create directory
    storage_path_exists = os.path.exists(staging_storage_location)
    if(storage_path_exists == False):
        os.mkdir(staging_storage_location, 777)


def get_articles():
    obj = Article()
    articles = obj.get_articles()
    # log = Log()
    # log.write_log_in_file("info", articles)
    # print("articles")
    # print(articles)

if __name__ == "__main__":
    main()
    print("try fetching articles....")
    get_articles()
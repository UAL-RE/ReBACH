import os
from Log import Log
from figshare.Article import Article
from time import asctime
from Config import Config
from figshare.Collection import Collection


def main():
    """
    This function will be called first.
    Setting up required variables and conditions.
    """
    log = Log()
    # Check .env file exist.
    file_exists = os.path.exists(".env.ini")

    if (file_exists is False):
        print(asctime() + ":ERROR: Log - " + "Please setup .env.ini file from .env.sample.ini file.")
        exit()

    config_obj = Config()
    figshare_config = config_obj.figshare_config()
    system_config = config_obj.system_config()
    figshare_api_url = figshare_config["url"]

    log_location = system_config["logs_location"]
    staging_storage_location = system_config["staging_storage_location"]
    figshare_api_token = figshare_config["token"]
    curation_storage_location = system_config["curation_storage_location"]

    # Check required env variables exist.
    if (log_location == ""):
        print(asctime() + ":ERROR: Log - " + "Logs file path missing in .env.ini file.")
        exit()

    if (figshare_api_url == "" or figshare_api_token == ""):
        log.write_log_in_file('error', "Figshare API URL and Token is required.", True, True)

    if (staging_storage_location == ""):
        log.write_log_in_file('error', "Staging storage location path is required.", True, True)

    if (curation_storage_location == ""):
        log.write_log_in_file('error', "Curation storage location path is required.", True, True)

    # Check logs path exits, if not then create directory
    logs_path_exists = os.path.exists(log_location)
    if (logs_path_exists is False):
        os.makedirs(log_location, exist_ok=True)

    # Check storage path exits, if not then give error and stop processing
    storage_path_exists = os.path.exists(staging_storage_location)
    access = os.access(staging_storage_location, os.W_OK)
    if (storage_path_exists is False or access is False):
        log.write_log_in_file('error',
                              "The staging storage location specified in the config file could not be reached or read.",
                              True, True)

    # Check curation path exits, if not then give error and stop processing
    curation_path_exists = os.path.exists(curation_storage_location)
    if (curation_path_exists is False):
        log.write_log_in_file('error',
                              "The curation staging storage location specified in the config file could"
                              + "not be reached or read.",
                              True, True)


def get_articles():
    """
    Creating article class object and sending call to process articles, setup metadata and download files.
    """
    obj = Article()
    article_data = obj.get_articles()
    return article_data
    # print("article_data=====")
    # print(article_data)
    # obj.process_articles(article_data)


def get_collections():
    """
    Creating collections class object and sending call to process collections and setup metadata.
    """
    obj = Collection()
    collection_data = obj.get_collections()
    return collection_data


if __name__ == "__main__":
    main()
    print("try fetching articles....")
    article_obj = Article()
    article_data = article_obj.get_articles()
    print("file size....")
    print(article_obj.total_all_articles_file_size)
    # print("try fetching collections....")
    # collection_obj = Collection()
    # collection_data = collection_obj.get_collections()

    article_obj.process_articles(article_data, article_obj.total_all_articles_file_size)

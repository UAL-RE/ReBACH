import os
from Log import Log
from figshare.Article import Article
from time import asctime
from Config import Config
from figshare.Collection import Collection


def check_logs_path_access():
    """
    Checking logs path access
    """
    config_obj = Config()
    system_config = config_obj.system_config()
    log_location = system_config["logs_location"]

    # Check logs path exits, if not then create directory
    logs_path_exists = os.path.exists(log_location)

    try:
        if (logs_path_exists is False):
            os.makedirs(log_location, mode=777, exist_ok=True)

        logs_access = os.access(log_location, os.W_OK)
        if (logs_access is False):
            print(asctime() + ":ERROR: Log - " + "The logs location specified in the config file could not be reached or read.")
            exit()

    except OSError as error:
        print(error)
        print(asctime() + ":ERROR: Log - " + "The logs location specified in the config file could not be reached or read.")
        exit()


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
    preservation_storage_location = system_config["preservation_storage_location"]
    figshare_api_token = figshare_config["token"]
    curation_storage_location = system_config["curation_storage_location"]

    # Check required env variables exist.
    if (log_location == ""):
        print(asctime() + ":ERROR: Log - " + "Logs file path missing in .env.ini file.")
        exit()

    if (figshare_api_url == "" or figshare_api_token == ""):
        log.write_log_in_file('error', "Figshare API URL and Token is required.", True, True)

    if (preservation_storage_location == ""):
        log.write_log_in_file('error', "Preservation storage location path is required.", True, True)

    if (curation_storage_location == ""):
        log.write_log_in_file('error', "Curation storage location path is required.", True, True)

    check_logs_path_access()
    # Check storage path exits, if not then give error and stop processing
    storage_path_exists = os.path.exists(preservation_storage_location)
    access = os.access(preservation_storage_location, os.W_OK)
    if (storage_path_exists is False or access is False):
        log.write_log_in_file('error',
                              "The preservation storage location specified in the config file could not be reached or read.",
                              True, True)

    # Check curation path exits, if not then give error and stop processing
    curation_path_exists = os.path.exists(curation_storage_location)
    curation_folder_access = os.access(curation_storage_location, os.W_OK)
    if (curation_path_exists is False or curation_folder_access is False):
        log.write_log_in_file('error',
                              "The curation storage location specified in the config file could"
                              + "not be reached or read.",
                              True, True)


def get_articles():
    """
    Creating article class object and sending call to process articles, setup metadata and download files.
    """
    obj = Article()
    article_data = obj.get_articles()
    return article_data


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

    print("try fetching collections....")
    collection_obj = Collection()
    collection_data = collection_obj.get_collections()

    # Start articles processing after completing fetching data from API
    article_obj.process_articles(article_data, article_obj.total_all_articles_file_size)

    # Start collections processing after completing fetcing data from API and articles processing.
    collection_obj.process_collections(collection_data)

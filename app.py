import os
from Log import Log
from figshare.Article import Article
from time import asctime
from Config import Config
from figshare.Collection import Collection
import sys


def check_logs_path_access(config_file):
    """
    Checking logs path access
    """
    config_obj = Config(config_file)
    system_config = config_obj.system_config()
    log_location = system_config["logs_location"]

    # Check logs path exists, if not then create directory
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


def get_config_file_path():
    args = sys.argv

    if (len(args) == 1 or args[1] == ''):
        print(asctime() + ":ERROR: Log - " + "First parameter must be configuration (.ini) file.")
        exit()

    path_val = args[1]
    path_val = path_val.strip()
    check_path = path_val.split('.')[-1]
    if (check_path != 'ini'):
        print(asctime() + ":ERROR: Log - " + "Configuration file extension must be .ini .")
        exit()

    file_exists = os.path.exists(path_val)

    if (file_exists is False):
        print(asctime() + ":ERROR: Log - " + "Configuration file is missing on the given path.")
        exit()

    return path_val


def main():
    print(asctime() + ":Info: Log - ReBACH script has started.")
    """
    This function will be called first.
    Setting up required variables and conditions.
    """
    # Check .env file exists.
    env_file = get_config_file_path()
    print(asctime() + ":Info: Log - " + "Env file:" + env_file)
    print(asctime() + ":Info: Log - " + "Checking configuration file.")
    config_obj = Config(env_file)

    figshare_config = config_obj.figshare_config()
    system_config = config_obj.system_config()
    figshare_api_url = figshare_config["url"]
    log = Log(env_file)
    log_location = system_config["logs_location"]
    preservation_storage_location = system_config["preservation_storage_location"]
    figshare_api_token = figshare_config["token"]
    curation_storage_location = system_config["curation_storage_location"]
    institution = figshare_config["institution"] if ("institution" in figshare_config and figshare_config["institution"] is not None) else 0

    # Check required env variables exist.
    if (log_location == ""):
        print(asctime() + ":ERROR: Log - " + "Logs file path missing in .env.ini file.")
        exit()

    log.write_log_in_file('info', "Logs location is accessible. Logging will now start.", True)

    if (figshare_api_url == "" or figshare_api_token == ""):
        log.write_log_in_file('error', "Figshare API URL and Token is required.", True, True)

    if (preservation_storage_location == ""):
        log.write_log_in_file('error', "Preservation storage location path is required.", True, True)

    if (curation_storage_location == ""):
        log.write_log_in_file('error', "Curation storage location path is required.", True, True)

    if (institution is None or institution == ''):
        log.write_log_in_file('error', "Institution Id is required.", True, True)

    log.write_log_in_file('info', "Configuration file meets requirements.", True)
    check_logs_path_access(env_file)
    # Check storage path exists, if not then give error and stop processing
    preservation_path_exists = os.path.exists(preservation_storage_location)
    access = os.access(preservation_storage_location, os.W_OK)
    if (preservation_path_exists is False or access is False):
        log.write_log_in_file('error',
                              "The preservation storage location specified in the config file could not be reached or read.",
                              True, True)

    # Check curation path exists, if not then give error and stop processing
    curation_path_exists = os.path.exists(curation_storage_location)
    curation_folder_access = os.access(curation_storage_location, os.W_OK)
    if (curation_path_exists is False or curation_folder_access is False):
        log.write_log_in_file('error',
                              "The curation storage location specified in the config file could"
                              + "not be reached or read.",
                              True, True)

    return env_file


if __name__ == "__main__":
    config_file_path = main()
    log = Log(config_file_path)

    log.write_log_in_file('info',
                          "Fetching articles...",
                          True)
    article_obj = Article(config_file_path)
    article_data = article_obj.get_articles()
    log.write_log_in_file('info',
                          f"Total articles fetched: {len(article_data)}.",
                          True)
    print(" ")

    log.write_log_in_file('info',
                          "Fetching collections...",
                          True)
    collection_obj = Collection(config_file_path)
    collection_data = collection_obj.get_collections()
    log.write_log_in_file('info',
                          f"Total collections fetched: {len(collection_data)}.",
                          True)
    print(" ")

    # Start articles processing after completing fetching data from API
    article_obj.process_articles(article_data, article_obj.total_all_articles_file_size)

    # Start collections processing after completing fetching data from API and articles processing.
    collection_obj.process_collections(collection_data)

    log.write_log_in_file('info', "ReBACH script has successfully finished.", True, True)

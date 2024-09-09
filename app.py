import os
import argparse
from version import __version__, __commit__
from Log import Log
from figshare.Article import Article
from datetime import datetime
from Config import Config
from figshare.Collection import Collection
from pathlib import Path

args = None


def get_args():
    """
    Parse command line arguments
    """
    global args
    parser = argparse.ArgumentParser(description='ReDATA preservation software (ReBACH)', prog='ReBACH', allow_abbrev=False)
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__ + ' Git-SHA: ' + __commit__)
    parser.add_argument('--xfg', required=True, type=Path, help='Path to the ReBACH configuration file. E.g., .env.ini')
    parser.add_argument('--ids', type=lambda s: [int(item) for item in s.split(',')],
                        help='list of article and/or collection IDs to process. E.g., "2323,4353,5454"')
    parser.add_argument('--continue-on-error', action='store_true',
                        help='If an item encounters an error during the processing stage, continue to the next item.')
    args = parser.parse_args()


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
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":ERROR: "
                  + "The logs location specified in the config file could not be reached or read.")
            exit()

    except OSError as error:
        print(error)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":ERROR: "
              + "The logs location specified in the config file could not be reached or read.")
        exit()


def main():
    """
    This function will be called first, after parsing the command line.
    Set up required variables and conditions.
    """
    global args
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":INFO: ReBACH script has started.")

    # Check .env file exists.
    if not args.xfg.is_file():
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":ERROR: " + "Configuration file is missing or cannot be read.")
        exit()
    env_file = str(args.xfg)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":INFO: " + "Env file:" + env_file)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":INFO: " + "Checking configuration file.")
    config_obj = Config(env_file)

    config_obj.add_setting(name='continue-on-error', value=args.continue_on_error)

    figshare_config = config_obj.figshare_config()
    system_config = config_obj.system_config()
    figshare_api_url = figshare_config["url"]
    log = Log(env_file)
    log_location = system_config["logs_location"]
    preservation_storage_location = system_config["preservation_storage_location"]
    figshare_api_token = figshare_config["token"]
    curation_storage_location = system_config["curation_storage_location"]
    post_process_script_command = system_config["post_process_script_command"]
    institution = figshare_config["institution"] if ("institution" in figshare_config and figshare_config["institution"] is not None) else 0

    # Check required env variables exist.
    if (log_location == ""):
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":ERROR: " + "Logs file path missing in .env.ini file.")
        exit()

    log.write_log_in_file('info', "Logs location is accessible. Logging to file will now start.", True)

    if (figshare_api_url == "" or figshare_api_token == ""):
        log.write_log_in_file('error', "Figshare API URL and Token is required.", True, True)

    if (preservation_storage_location == ""):
        log.write_log_in_file('error', "Preservation storage location path is required.", True, True)

    if (curation_storage_location == ""):
        log.write_log_in_file('error', "Curation storage location path is required.", True, True)

    if (post_process_script_command == ""):
        log.write_log_in_file('error', "post process script command is required.", True, True)

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
    curation_folder_access = os.access(curation_storage_location, os.R_OK)
    if (curation_path_exists is False or curation_folder_access is False):
        log.write_log_in_file('error',
                              "The curation storage location specified in the config file could"
                              + "not be reached or read.",
                              True, True)

    # Check if the path to the post-processing external script exists and if the folder is accessible
    if (post_process_script_command != "Bagger"):
        post_process_script_path_exists = os.path.exists(post_process_script_command)
        post_process_script_folder_access = os.access(post_process_script_command, os.W_OK)
        if (post_process_script_path_exists is False or post_process_script_folder_access is False):
            log.write_log_in_file('error',
                                  "The post process script location specified in the config file could"
                                  + " not be reached or read.",
                                  True, False)

    return config_obj, log


if __name__ == "__main__":
    get_args()
    config, log = main()

    log.write_log_in_file('info',
                          "Fetching articles...",
                          True)
    article_obj = Article(config, log, args.ids)
    article_data, already_preserved_counts_dict = article_obj.get_articles()

    already_preserved_articles_count = len(already_preserved_counts_dict['already_preserved_article_ids'])
    already_preserved_versions_count = already_preserved_counts_dict['already_preserved_versions']
    published_articles_count = 0
    published_articles_versions_count = 0
    published_unpublished_count = 0

    for i, (k, v) in enumerate(article_data.items()):
        published_unpublished_count += 1
        if len(v) > 0:
            published_articles_count += 1
            published_articles_versions_count += len(v)

    log.write_log_in_file('info', "Fetched: "
                          + f"Total articles: {published_unpublished_count}, "
                          + f"Published articles: {published_articles_count + already_preserved_articles_count}, "
                          + f"Published article versions: {published_articles_versions_count + already_preserved_versions_count}",
                          True)
    print(" ")

    log.write_log_in_file('info',
                          "Fetching collections...",
                          True)
    collection_obj = Collection(config, log, args.ids)
    collection_data = collection_obj.get_collections()

    collections_count = 0
    collections_versions_count = 0
    for i, (k, v) in enumerate(collection_data.items()):
        collections_count += 1
        collections_versions_count += len(v['versions'])
    log.write_log_in_file('info',
                          f"Total collections fetched: {collections_count}. Total collections versions fetched: {collections_versions_count}.",
                          True)
    print(" ")

    # Start articles processing after completing fetching data from API
    processed_articles_versions_count, ap_trust_preserved_article_version_count, wasabi_preserved_versions \
        = article_obj.process_articles(article_data)

    # Start collections processing after completing fetching data from API and articles processing.
    processed_collections_versions_count, already_preserved_collections_counts = collection_obj.process_collections(collection_data)
    already_preserved_collections = len(already_preserved_collections_counts['already_preserved_collection_ids'])
    already_preserved_collection_versions = already_preserved_collections_counts['already_preserved_versions']
    preserved_collection_versions_in_wasabi = already_preserved_collections_counts['wasabi_preserved_versions']
    preserved_collection_versions_in_ap_trust = already_preserved_collections_counts['ap_trust_preserved_versions']

    log.write_log_in_file('info', '------- Summary -------')
    log.write_log_in_file('info',
                          "Total articles/published articles: \t\t\t\t\t\t\t\t"
                          + f'{published_unpublished_count} / {published_articles_count + already_preserved_articles_count}',
                          True)

    log.write_log_in_file('info',
                          "Total count of already(skipped) preserved articles: \t\t\t\t\t"
                          + f'{already_preserved_articles_count}',
                          True)

    log.write_log_in_file('info',
                          "Total count of already(skipped) preserved article versions: \t\t\t"
                          + f'{already_preserved_versions_count}',
                          True)

    if article_obj.processor.duplicate_bag_in_preservation_storage_count > 0:
        log.write_log_in_file('warning',
                              f'Bagger found {article_obj.processor.duplicate_bag_in_preservation_storage_count} duplicate article(s)',
                              True)

    log.write_log_in_file('info',
                          "Total articles versions matched/published: \t\t\t\t\t\t"
                          + f'{article_obj.no_matched} / {published_articles_versions_count}',
                          True)
    log.write_log_in_file('info',
                          "Total articles versions processed/matched: \t\t\t\t\t\t"
                          + f'{processed_articles_versions_count} / {article_obj.no_matched}',
                          True)
    log.write_log_in_file('info',
                          "Total count of already preserved articles versions in preservation final remote storage: \t\t\t\t"
                          + f'{ap_trust_preserved_article_version_count}',
                          True)
    log.write_log_in_file('info',
                          "Total count of already preserved articles versions in preservation staging remote storage: \t\t\t"
                          + f'{wasabi_preserved_versions}',
                          True)

    log.write_log_in_file('info',
                          "Total articles versions unmatched (published-matched): \t\t\t\t"
                          + f'{article_obj.no_unmatched}',
                          True)
    log.write_log_in_file('info',
                          "Total processed articles bags successfully preserved: \t\t\t\t"
                          + f'{article_obj.processor.bag_preserved_count}',
                          True)
    log.write_log_in_file('info',
                          "Total collections/published collections: \t\t\t\t\t\t\t"
                          + f'{collections_count} / {collections_count}',
                          True)

    log.write_log_in_file('info',
                          "Total count of already(skipped) preserved collections: \t\t\t\t"
                          + f'{already_preserved_collections}',
                          True)

    log.write_log_in_file('info',
                          "Total count of already(skipped) preserved collection versions: \t\t"
                          + f'{already_preserved_collection_versions}',
                          True)

    log.write_log_in_file('info',
                          "Total collections versions processed/published: \t\t\t\t\t"
                          + f'{processed_collections_versions_count} / {collections_versions_count - already_preserved_collection_versions}',
                          True)


    if collection_obj.processor.duplicate_bag_in_preservation_storage_count > 0:
        log.write_log_in_file('warning',
                              f'Bagger found {collection_obj.processor.duplicate_bag_in_preservation_storage_count} duplicate collection(s)',
                              True)



    log.write_log_in_file('info',
                          "Total count of already preserved collections versions in preservation final remote storage: \t\t\t"
                          + f'{preserved_collection_versions_in_ap_trust}',
                          True)

    log.write_log_in_file('info',
                          "Total count of already preserved collections versions in preservation staging remote storage: \t\t"
                          + f'{preserved_collection_versions_in_wasabi}',
                          True)

    if processed_articles_versions_count != published_articles_versions_count or \
            processed_collections_versions_count != (collections_versions_count - already_preserved_collection_versions):
        log.write_log_in_file('warning',
                              'The number of articles versions or collections versions successfully processed is different'
                              + ' than the number fetched. Check the log for details.', True)

    log.write_log_in_file('info',
                          f"ReBACH finished with {log.warnings_count} warnings and {log.errors_count} errors",
                          True)

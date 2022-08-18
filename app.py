from dotenv import load_dotenv
import os
from Log import Log
from time import asctime

load_dotenv()

def main():
    log = Log()
    # Check .env file exist.
    file_exists = os.path.exists(".env")

    if(file_exists == False):
        print(asctime() + ":ERROR: Log - " + "Please setup .env file from .env.sample file.")
        exit()

    figshare_api_url = os.getenv("FIGSHARE_ENDPOINT")
    log_location = os.getenv("LOGS_LOCATION")
    staging_storage_location = os.getenv("STAGING_STORAGE_LOCATION")
    figshare_api_token = os.getenv("FIGSHARE_TOKEN")
    
    # Check required env variables exist.
    if(log_location == ""):
        print(asctime() + ":ERROR: Log - " + "Logs file path missing in .env file.")
        exit()

    if(figshare_api_url == "" or figshare_api_token == ""):
        log.write_log_in_file('error', "Figshare API URL and Token is required.", True)
    
    if(staging_storage_location == ""):
        log.write_log_in_file('error', "Stagin storage location path is required.", True)

    #Check logs path exits, if not then create directory
    logs_path_exists = os.path.exists(log_location)
    if(logs_path_exists == False):
        os.mkdir(logs_path_exists, 777)

    #Check storage path exits, if not then create directory
    storage_path_exists = os.path.exists(staging_storage_location)
    if(storage_path_exists == False):
        os.mkdir(staging_storage_location, 777)
    


if __name__ == "__main__":
    main()
    print("checking....")
from dotenv import load_dotenv
import os
from Log import Log

load_dotenv()

def main():
    figshare_api_url = os.getenv("FIGSHARE_ENDPOINT")
    log_location = os.getenv("LOGS_LOCATION")
    if(figshare_api_url == ""):
        Log.write_log_in_file('error', "Figshare API URL is required.")
    if(log_location == ""):
        Log.write_log_in_file('error', "Logs location path is required.")

if __name__ == "__main__":
    main()
    print("checking....")
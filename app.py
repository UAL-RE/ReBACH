from dotenv import load_dotenv
import os
from Log import Log
from figshare.Article import Article

load_dotenv()

def main():
    figshare_api_url = os.getenv("FIGSHARE_ENDPOINT")
    log_location = os.getenv("LOGS_LOCATION")
    log = Log()
    if(figshare_api_url == ""):
        # log.write_log_in_file('error', "Figshare API URL is required.")
        log.show_log_in_terminal('info', "Figshare API URL is required.")
    if(log_location == ""):
        # log.write_log_in_file('error', "Logs location path is required.")
        log.show_log_in_terminal('info', "Logs location path is required.")

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
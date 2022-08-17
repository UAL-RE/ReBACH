from datetime import datetime
import logging
import os

class LogToFile:

    def write_log_in_file(self, type, message):
        log_location = os.getenv("LOGS_LOCATION")
        file_name = "log-" + datetime.now().strftime("%Y-%m-%d") + ".log"
        if(log_location[-1] != "/"):
            log_location = log_location + '/'

        file_path = log_location + file_name
        logging.basicConfig(filename = file_path,
                    format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s')
                    
        if(type == 'warning'):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.WARNING)
            logger.warning(message)
            del logger
        elif(type == 'info'):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.INFO)
            logger.info(message)
            del logger
        elif(type == 'debug'):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)
            logger.debug(message)
            del logger
        else:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.ERROR)
            logger.error(message)
            del logger
            exit()
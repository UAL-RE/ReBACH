from datetime import datetime
import logging
from Config import Config


# Log class to handle log messages
class Log:
    def __init__(self, config):
        self.config = config
        file_name = "log-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"

        # Setup log configration
        config_obj = Config(self.config)
        system_config = config_obj.system_config()
        log_location = system_config["logs_location"]

        if (log_location[-1] != "/"):
            log_location = log_location + '/'
        self.file_path = log_location + file_name

    def log_config(self, in_terminal: bool = False):
        if (in_terminal):
            f = ''
        else:
            f = self.file_path
        logging.basicConfig(filename=f, force=True,
                            format="%(asctime)s:%(levelname)s: %(message)s")

    def show_log_in_terminal(self, type, message, stop_script=False):
        # Show log in terminal
        self.log_config(True)
        self.message(type, message)
        if (stop_script is True):
            exit()

    def write_log_in_file(self, type, message, show_in_terminal=False, stop_script=False):
        # Show log in file
        self.log_config(False)
        if (show_in_terminal is True):
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":" + type.upper() + ": " + message)
        self.message(type, message)
        if (stop_script is True):
            exit()

    def message(self, type, message):
        if (type == 'warning'):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.WARNING)
            logger.warning(message)
            del logger
        elif (type == 'info'):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.INFO)
            logger.info(message)
            del logger
        elif (type == 'debug'):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)
            logger.debug(message)
            del logger
        else:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.ERROR)
            logger.error(message)
            del logger


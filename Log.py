from datetime import datetime
import logging
import ctypes
import platform
import sys
import os
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

        self.ansi_terminal = _check_ansi()
        self.warnings_count = 0
        self.errors_count = 0

    def log_config(self, in_terminal: bool = False):
        if (in_terminal):
            f = ''
            logging.addLevelName(logging.WARNING, self._format_messagetype_ansi('WARNING'))
            logging.addLevelName(logging.ERROR, self._format_messagetype_ansi('ERROR'))
        else:
            f = self.file_path
        logging.basicConfig(filename=f, force=True,
                            format='%(asctime)s:%(levelname)s: %(message)s')

    def show_log_in_terminal(self, type, message, stop_script=False):
        # Show log in terminal
        self.log_config(True)
        self._count_errorwarning(type)
        self.message(type, message)
        if (stop_script is True):
            exit()

    def write_log_in_file(self, type, message, show_in_terminal=False, stop_script=False):
        # Show log in file
        self.log_config(False)
        self._count_errorwarning(type)
        if (show_in_terminal is True):
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3] + ":" + self._format_messagetype_ansi(type.upper()) + ": " + message)
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

    def _count_errorwarning(self, msgtype):
        '''
        Counts how many times a message type (string) of warning or error is passed in
        '''
        if msgtype.lower() == 'warning':
            self.warnings_count += 1
        if msgtype.lower() == 'error':
            self.errors_count += 1

    def _format_messagetype_ansi(self, type):
        '''
        Returns a colorized version of the given message type string. If no ANSI support is detected, the same string is returned unchanged.
        '''
        if not self.ansi_terminal:
            return type
        if (type.lower() == 'error'):
            return '\033[2;30;41m' + type + '\033[0;0m'
        elif (type.lower() == 'warning'):
            return '\033[2;31;43m' + type + '\033[0;0m'
        elif (type.lower() == 'info'):
            return type
        elif (type.lower() == 'debug'):
            return type
        else:
            return type


def _check_ansi():
    '''
    Returns True if the terminal the script is being run in supports ANSI escape sequences
    Based on: https://gist.github.com/ssbarnea/1316877
    '''
    for handle in [sys.stdout, sys.stderr]:
        if (hasattr(handle, "isatty") and handle.isatty()) or ('TERM' in os.environ and os.environ['TERM'] == 'ANSI'):
            if platform.system() == 'Windows' and not ('TERM' in os.environ and os.environ['TERM'] == 'ANSI'):
                if _is_wt():
                    # Windows terminal does support ANSI
                    return True
                else:
                    # Assume the console does not support ANSI
                    return False
            else:
                # Assume ANSI available
                return True
        else:
            # no ANSI available
            return False


def _is_wt():
    '''
    Returns True if the script is run in the Windows Terminal 'wt.exe'
    Source: https://github.com/cvzi/AssertWT/blob/3125863ef823d5eaad1bc55155d90d9ca83f4aec/assertwt.py#L74-L88
    '''

    if platform.system() != 'Windows' or 'idlelib' in sys.modules:
        return False

    window = ctypes.windll.kernel32.GetConsoleWindow()
    if not window:
        return False
    ctypes.windll.kernel32.CloseHandle(window)
    WM_GETICON = 0x7F
    ret = ctypes.windll.user32.SendMessageW(window, WM_GETICON, 0, 0)
    return not ret

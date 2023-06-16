import os
import sys
from pathlib import Path
from redata.commons import logger
from bagger.bag import Bagger, Status
from bagger.config import get_args, TOMLDecodeError
from Config import Config
from Log import Log


class Integration:

    def __init__(self, config: Config, log: Log):
        """
        Class constructor.

        :param config: ReBACH configuration object
        :param log: ReBACH logger object
        """
        self._config = config
        self._rebachlogger = log

    """
    Post-processing script command function.
    """
    def post_process_script_function(self, *args):
        """
        Execute a post-processing script on an article or collection package and return the result.

        If the 'post_process_script_command' value in the configuration file is set to 'Bagger', this function
        will execute the post-processing script internally. Otherwise, it will expect the value to be a path
        to an external script, which will be called.

        :param args: Variable-length arguments passed to the function.
                     args[0]: 'Article' or 'Collection' to indicate whether the function is called from an Article or Collection.
                     args[1]: Path to the article or collection package.
                     args[2]: (optional, for article only): Result of the pre-processing script.
        """
        package = args[0]
        preservation_package_path = args[1]

        if (package == "Article"):
            # Acting on value_pre_process is not currently implemented and is commented out until needed.
            # value_pre_process = args[2]
            pass

        post_process_script_command = self._config.system_config()["post_process_script_command"]

        if (post_process_script_command == "Bagger"):
            try:
                args, config = get_args()
            except TOMLDecodeError as e:
                self._rebachlogger.write_log_in_file("error", f"Error in configuration file: {e.filename}.", True)
                self._rebachlogger.write_log_in_file("error", f"TOML Decode Error: {e}.", True)
                sys.exit(Status.INVALID_CONFIG)

            self._rebachlogger.write_log_in_file("info", f"Config file: {args.config}", True)

            log_dir = config['Logging']['log_dir']
            if self._config.system_config() is not None:
                # Override the log directory specified in the toml config of bagger with the main ReBACH config, if available.
                log_dir = self._config.system_config()["logs_location"]
                self._rebachlogger.write_log_in_file("info", f"Overriding bagger log file location {config['Logging']['log_dir']} with "
                                                           + f"{log_dir} from ReBACH Env file", True)

            logfile_prefix = config['Logging']['logfile_prefix']

            # This is the bagger logger, which uses a different class. TODO: use the same logger as the main program
            log = logger.log_setup(log_dir, logfile_prefix)

            os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
            os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

            args.path = preservation_package_path

            preservation_package_name = os.path.basename(preservation_package_path)
            bagger = Bagger(workflow=args.workflow, output_dir=args.output_dir,
                            delete=args.delete, dart_command=args.dart_command,
                            config=config, log=log, overwrite=args.overwrite, dryrun=False)

            if args.batch:
                self._rebachlogger.write_log_in_file("info", "Batch mode", True)
                self._rebachlogger.write_log_in_file("info", f" Batch path: {args.path}", True)
                for _path in next(os.walk(args.path))[1]:
                    bagger.run_dart(Path(args.path, _path))
            else:
                self._rebachlogger.write_log_in_file("info", f"Processing preservation package '{preservation_package_name}' ", True)
                status = bagger.run_dart(args.path)
                self._rebachlogger.write_log_in_file("info", f"Status: {status.name}.", True)
                self._rebachlogger.write_log_in_file("info", f"Exit code: {status}.", True)
                if (status == 0):
                    self._rebachlogger.write_log_in_file("info", f"Preservation package '{preservation_package_name}' processed successfully", True)
                    return 0
                elif (status == 3):
                    self._rebachlogger.write_log_in_file("warning", f"'{preservation_package_name}' already exists in "
                                                + f"{config['Wasabi']['host']}/{config['Wasabi']['bucket']}. File not uploaded.", True)
                    return 0
                else:
                    return status
        else:
            self._rebachlogger.write_log_in_file("info", f"[not implemented] Executing post-processing script Command: {post_process_script_command}.", True)
            return 0

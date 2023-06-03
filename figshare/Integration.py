import os
import sys
import ast
from pathlib import Path
from redata.commons import logger
from bagger.bag import Bagger, Status
from bagger.config import get_args, TOMLDecodeError


class Integration:

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

        post_process_script_command = self.system_config["post_process_script_command"]

        if (post_process_script_command == "Bagger"):
            try:
                args, config = get_args()
            except TOMLDecodeError as e:
                self.logs.write_log_in_file("Info", f"Error in configuration file: {e.filename}.", True)
                self.logs.write_log_in_file("Info", f"TOML Decode Error: {e}.", True)
                sys.exit(Status.INVALID_CONFIG)

            log_dir = config['Logging']['log_dir']
            logfile_prefix = config['Logging']['logfile_prefix']

            log = logger.log_setup(log_dir, logfile_prefix)

            self.logs.write_log_in_file("Info", f"Config file: {args.config}", True)

            os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
            os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

            args.path = preservation_package_path

            preservation_package_name = os.path.basename(preservation_package_path)
            bagger = Bagger(workflow=args.workflow, output_dir=args.output_dir,
                            delete=args.delete, dart_command=args.dart_command,
                            config=config, log=log, overwrite=args.overwrite, dryrun=False)

            if args.batch:
                self.logs.write_log_in_file("Info", "Batch mode", True)
                self.logs.write_log_in_file("Info", f" Batch path: {args.path}", True)
                for _path in next(os.walk(args.path))[1]:
                    bagger.run_dart(Path(args.path, _path))
            else:
                self.logs.write_log_in_file("Info", f"Processing preservation package '{preservation_package_name}' ", True)
                status = bagger.run_dart(args.path)
                self.logs.write_log_in_file("Info", f"Status: {status.name}.", True)
                self.logs.write_log_in_file("Info", f"Exit code: {status}.", True)
                if (status == 0):
                    self.logs.write_log_in_file("Info", f"Preservation package '{preservation_package_name}' processed successfully", True)
                    return 0
                elif (status == 3):
                    return 0
                else:
                    return status
        else:
            self.logs.write_log_in_file("Info", f"Executing post-processing script Command: {post_process_script_command}.", True)
            return 0
        
    def get_id_list(self):

        """
        Get the list of article and collection IDs from command-line arguments.

        If the command-line argument count is greater than 2, extract the argument string
        representing the list of IDs from sys.argv[3]. Parse the argument string into a list
        using ast.literal_eval() and return the resulting ID list.

        Returns:
        list: A list of article and collection IDs extracted from command-line arguments.
        """

        id_list = []

        if len(sys.argv) > 2:
            if "--Ids" in sys.argv:
                index = sys.argv.index("--Ids")
                if len(sys.argv) > index + 1:
                    arg_str = sys.argv[index + 1]
                    id_list = ast.literal_eval(arg_str)  # Parse the argument string into a list
                else:
                    self.logs.write_log_in_file("error", "No value provided after --Ids", True, True)

        return id_list

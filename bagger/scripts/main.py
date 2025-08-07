import os
import sys
from inspect import signature
from pathlib import Path

from redata.commons import logger, git_info

from bagger.bag import Bagger, Status
from bagger.config import get_args, TOMLDecodeError


class LogCommons(logger.LogCommons):
    """
    Override LogCommons.script_end method to allow printing a non-0 exit code
        First check if the base method signature has been modified
    """
    if "exit_code" not in signature(logger.LogCommons.script_end).parameters:
        def script_end(self, exit_code: int = 0) -> None:
            self.log.info(self.asterisk)
            self.log.info(f"Exit {exit_code}")


# TODO: Initialization can be made into a self-contained initialization
#  function
def main() -> None:
    init_log = logger.log_stdout()
    library_root_path = Path(__file__).resolve().parents[2]

    gi = git_info.GitInfo(str(library_root_path))

    try:
        args, config = get_args()
    except TOMLDecodeError as e:
        init_log.error(f"Error in configuration file: {e.filename}")
        init_log.error(f"  TOML Decode Error: {e}")
        sys.exit(Status.INVALID_CONFIG)

    log_dir = config['Logging']['log_dir']
    logfile_prefix = config['Logging']['logfile_prefix']

    log = logger.log_setup(log_dir, logfile_prefix)

    lc = LogCommons(log, 'ReBACH_Bagger-Main', gi)
    lc.script_start()
    lc.script_sys_info()

    log.info(f'Library root path: {library_root_path}')
    log.info(f'Config file: {args.config}')

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

    bagger = Bagger(workflow=args.workflow, archival_staging_storage=args.archival_staging_storage,
                    delete=args.delete, dart_command=args.dart_command,
                    config=config, log=log, overwrite=args.overwrite, dryrun=args.dry_run)

    if args.batch:
        log.info('Batch mode')
        log.info(f'  Batch path: {args.path}')
        for _path in next(os.walk(args.path))[1]:
            bagger.run_dart(Path(args.path, _path))
        lc.script_end()
        lc.log_permission()

    else:
        status = bagger.run_dart(args.path)
        log.info(f'Status: {status.name}')
        log.info(f'Exit code: {status}')
        lc.script_end(status)
        lc.log_permission()
        sys.exit(status)


if __name__ == '__main__':
    main()

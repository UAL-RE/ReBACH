import os
import sys
from os import path

from redata.commons import logger, git_info

from redata_preservation.bagger.bag import Bagger
from redata_preservation.config import get_args


def main():
    args, config = get_args()

    library_root_path = path.dirname(path.dirname(__file__))
    gi = git_info.GitInfo(library_root_path)

    log_dir = config['Logging']['log_dir']
    logfile_prefix = config['Logging']['logfile_prefix']

    log = logger.log_setup(log_dir, logfile_prefix)

    lc = logger.LogCommons(log, 'ReDATA-P_main', gi)

    lc.script_start()
    lc.script_sys_info()

    os.environ['WASABI_ACCESS_KEY_ID'] = config['Wasabi']['access_key']
    os.environ['WASABI_SECRET_ACCESS_KEY'] = config['Wasabi']['secret_key']

    bagger = Bagger(workflow=args.workflow, output_dir=args.output_dir,
                    delete=args.delete, dart_command='dart-runner',
                    config=config, log=log)

    if args.batch:
        log.info('Batch mode')
        log.info(f'  Batch path: {args.path}')
        for _path in next(os.walk(args.path))[1]:
            bagger.run_dart(path.join(args.path, _path))
        lc.script_end()
        lc.log_permission()

    else:
        status = bagger.run_dart(args.path)
        log.info(f'Status: {status.name}')
        log.info(f'Exit code: {status.value}')
        lc.script_end()
        lc.log_permission()
        sys.exit(status.value)


if __name__ == '__main__':
    main()

# ReBACH-Bagger

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust DART tool, and uploading the completed bag to offsite storage.

## Usage

```text
$ python -m redata_preservation.scripts.main -h
usage: main.py [-h] [-c CONFIG] [-b BATCH] [-d | --delete | --no-delete]
               [-o OUTPUT_DIR] [-w WORKFLOW] [--dart_command DART_COMMAND]
               [--overwrite | --no-overwrite]
               path

positional arguments:
  path                  Path to the package or batch directory

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to configuration file.
  -b BATCH, --batch BATCH
                        Process a batch directory.
  -d, --delete, --no-delete
                        Delete bags after upload. (default: True)
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output directory for generated bags.
  -w WORKFLOW, --workflow WORKFLOW
                        Path to workflow file.
  --dart_command DART_COMMAND
                        Command to invoke DART Runner.
  --overwrite, --no-overwrite
                        Overwrite duplicate bags. (default: False)
```

## Configuration

ReBACH-Bagger uses [TOML-based](https://toml.io/en/) configuration files found
in the config directory.

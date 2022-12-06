# ReBACH-Bagger

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust DART tool, and uploading the completed bag to offsite storage.

## Usage

ReBACH-Bagger can be used on the command line by calling the `scripts/main.py`
file or running the main script as a module:

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

ReBACH-Bagger can also be imported as a module. The `main.py` script
contains an example of what this looks like in practice, but a simplified
example follows:

```python
# Import Bagger
from redata_preservation.bagger.bag import Bagger

# Instantiate Bagger with necessary arguments
B = Bagger(workflow, output_dir, delete, dart_command, config, log)

# Run DART on the package specified with path
run = B.run_dart(path)
```

## Configuration

ReBACH-Bagger uses [TOML-based](https://toml.io/en/) configuration files found
in the config directory. The `default.example.toml` file in the config
directory contains the configuration variables expected by ReBACH-Bagger. By
default, the program will look for a config file named `default.toml` in the
`rebach_bagger/config` directory. A config file can also be specified at
runtime using `--config` or `-c`. Paths in the config file are all relative to
the directory from which the script is called. Using absolute paths may be
advisable if ReBACH-Bagger will be imported as a module.

### Defaults

The `Defaults` section of the configuration file contains keys that define the
program's execution environment. The keys defined here can also be set at
runtime using the command line options described above. Command line
configuration options are first in precendce, meaning values passed with the
command line will override values set in the config file.

```toml
[Defaults]
output_dir = "out" # DART will output generated bags here; must be writable
workflow = "default_workflow.json" # Path to the DART workflow file
dart_command = "dart-runner" # Command or path to DART executable
```

### Logging

ReBACH-Bagger logs errors, debug messages, and DART output to disk.

```toml
[Logging]
log_dir = "logs" # Logger will write logs to this directory
logfile_prefix = "ReBACH-Bagger" # Log filename prefix
```

### Wasabi

Both DART and ReBACH-Bagger use the `access_key` and `secret_key` credentials
defined in the configuration to authenticate to Wasabi. However, only
ReBACH-Bagger uses the other variables defined here to access the storage
endpoint for the purpose of checking for duplicate bags. DART uses the storage
configuration embedded in the workflow JSON file for selecting the correct
endpoint. Verify that these values match.

```toml
[Wasabi]
name = "***override***"
host = "***override***"
bucket = "***override***"
host_bucket = "***override***"
access_key = "***override***"
secret_key = "***override***"
```

### Metadata

ReBACH-Bagger can apply a configurable set of metadata tags to the bags it
generates. These tags are defined in the `Metadata` section of the
configuration file. The tags are defined with the following schema:

`tag_file.tag_name = "tag_source"`

The `tag_source` element is a dot-notation path to the tag's corresponding key
in the package's metadata JSON file. Take the following abbreviated example of
Figshare's API metadata:

```json
{
  "authors": [
    {
      "full_name": "Brian Avants"
    },
    {
      "full_name": "Arno Klein"
    }
  ],
  "license": {
    "name": "Apache 2.0",
    "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
  },
  "title": "MNI space average T1-weighted MRI of the brain with anatomical labels.",
  "doi": "10.6084/m9.figshare.2066037.v17"
}
```

To define a set of tags named "First-Author", "License", and "DOI" in the "
bag-info.txt" tag file, users can define the following relationships in the
config file:

```toml
[Metadata]
bag-info.First-Author = "authors.0.full_name"
bag-info.License = "license.name"
bag-info.DOI = "doi"
```

## DART Workflow

## BagIt Profile
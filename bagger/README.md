# ReBACH-Bagger

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust DART tool, and uploading the completed bag to offsite storage.

## Setup

ReBACH-Bagger has a handful of dependencies that can be installed with PIP:

```text
$ pip install -r requirements.txt
```

These dependencies are [ReDATA Commons](https://github.com/UAL-RE/redata-commons), which Bagger uses
for logging;
[s3cmd](https://s3tools.org/s3cmd) for interacting with Wasabi; and the tomllib backport
[tomli](https://github.com/hukkin/tomli).

ReBACH-Bagger also depends on the
[DART Runner](https://aptrust.github.io/dart-docs/users/dart_runner/) executable being available in
the environment path. One simple way to do this is to download the executable to the Python virtual
environment bin directory:

```text
$ wget -P venv/bin https://s3.amazonaws.com/aptrust.public.download/dart-runner/v0.95-beta/linux-x64/dart-runner
$ chmod +x venv/bin/dart-runner
```

You may pass or configure a different path to DART runner using the `dart_command` directive in
the config file or `--dart_command` on the command line. See "DART Workflow" section below for
details on configuring DART.

## Usage

ReBACH-Bagger can be used on the command line by calling the `scripts/main.py`
file or running the main script as a module:

```text
$ python -m redata_preservation.scripts.main --help
usage: main.py [-h] [-c CONFIG] [-b BATCH] [-d | --delete | --no-delete] [-o OUTPUT_DIR]
               [-w WORKFLOW] [--dart_command DART_COMMAND] [--overwrite | --no-overwrite] [--dryrun]
               path

positional arguments:
  path                  Path to the package or batch directory.

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
  --dryrun              Log execution steps without executing. (default: False)
```

ReBACH-Bagger can also be imported as a module. The `main.py` script
contains an example of what this looks like in practice, but a simplified
example follows:

```python
# Import Bagger
from bagger.bag import Bagger

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
`bagger/config` directory. A config file can also be specified at
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

Both DART and ReBACH-Bagger use the `access_key` and `secret_key` credentials defined in the
configuration to authenticate to Wasabi (see below for details on how these variables are used in
DART). However, only ReBACH-Bagger uses the other variables defined here to access the endpoint for
the purpose of checking for duplicate bags. DART uses the storage configuration embedded in the
workflow JSON file for selecting the correct endpoint. Verify that these values match.

```toml
[Wasabi]
name = "***override***"
host = "***override***"
bucket = "***override***"
host_bucket = "***override***"
access_key = "***override***"
secret_key = "***override***"
```

## Metadata Configuration

ReBACH-Bagger can apply a configurable set of metadata tags to the bags it generates. These tags
are defined in the `Metadata` section of the configuration file. The tags are defined with the
following schema:

`# tag-file.Tag-Name = "Tag value"`

The `tag-file` element corresponds to the tag file (e.g. bag-info.txt) in which the tag will be
placed. Do not include `.txt` as part of the tag-file element.

`Tag-Name` is the name of the metadata tag. Conventionally, tag names are uppercase, dash-separated
words.

If the `"Tag value"` element is a string, ReBACH-Bagger will simply use the string as the value of
the tag.

### Metadata from JSON

Users may also use an inline table to define a dot-notation `tag_path` to the tag's corresponding 
key in the package's metadata file. Take the following abbreviated example of a metadata JSON file:

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

To define a set of tags based on this metadata named "First-Author", "License", and "DOI" in the 
"bag-info.txt" tag file, users can define the following relationships in the config file:

```toml
[Metadata]
bag-info.First-Author = { tag_path = "authors.0.full_name" }
bag-info.License = { tag_path = "license.name" }
bag-info.DOI = { tag_path = "doi" }
```

### Metadata Utilities

ReBACH-Bagger can strip HTML tags out of a metadata value. To enable this functionality, use a
TOML inline table to define a `tag_path` key and set the `strip_html` key to `true`. Optionally,
set the `shorten` key to the maximum number of characters to allow in the formatted value.
Shortening will truncate at word boundaries (see
[Python documentation](https://docs.python.org/3.9/library/textwrap.html#textwrap.shorten)), so
the resulting string may be shorter than the specified limit.

```toml
[Metadata]
aptrust-info.Description = { tag_path = "description", strip_html = true, shorten = 100 }
```

## DART Workflow

A [DART workflow](https://aptrust.github.io/dart-docs/users/workflows/) is a JSON file that
describes the packaging and upload operations that should be performed when a bag is created by
DART Runner. Users should create the workflow file using the desktop version of DART. Details
are available in the [DART documentation](https://aptrust.github.io/dart-docs/users/workflows/).

The workflow file will include a name, description, the backage format (BagIt) and a BagIt
profile (APTrust or a profile based on APTrust containing additional ReDATA-specific tags; see
below). The workflow will also include the storage location and credentials needed to upload
the bag.

When creating a new workflow with DART, users should NOT enter their AWS/Wasabi access key or
secret key into the workflow configuration. Instead, DART provides the option to access these
values [with an environment variable](https://aptrust.github.io/dart-docs/users/settings/storage_services/#login),
which ReBACH-Bagger will populate from the Wasabi credentials in the configuration file.

Instead of entering the access key ID into the login field, enter `env:WASABI_ACCESS_KEY_ID`.
For the password, enter `env:WASABI_SECRET_ACCESS_KEY`.

### BagIt Profile

The BagIt profile describes the metadata tags that are required or expected to be stored within
the bag. These tags include default tags common to all BagIt bags, tags required by APTrust, and
tags defined by the ReBACH-Bagger metadata configuration (see above). Profiles can
be created and
modified [using DART's desktop application](https://aptrust.github.io/dart-docs/users/bagit/).
Profiles are embedded in the DART workflow file and do not need to be separately provided to
ReBACH-Bagger.

# ReBACH-Bagger

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust [DART](https://github.com/APTrust/dart) tool, and uploading the completed bag to offsite storage.
Refer to the ReBACH specification (internal docs).

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
the config file or `--dart_command` on the command line. See [DART Workflow]("#dart-workflow") for
details on configuring DART.

## Usage

ReBACH-Bagger can be used on the command line by running the main script as a module:

```text
$ python -m bagger.scripts.main -h
usage: main.py [-h] [-c config_file] [-b batch_dir] [-d | --delete | --no-delete]
               [-o archival_staging_storage] [-w workflow_file] [--dart_command dart_command]
               [--overwrite | --no-overwrite] [--dry-run]
               path

positional arguments:
  path                  Path to the package or batch directory.

optional arguments:
  -h, --help            show this help message and exit
  -c config_file, --config config_file
                        Path to configuration file.
  -b batch_dir, --batch batch_dir
                        Process a batch directory.
  -d, --delete, --no-delete
                        Delete bags after upload. (default: True)
  -o archival_staging_storage, --archival_staging_storage archival_staging_storage
                        Output directory for generated bags if workflow is not configured to upload to a remote storage location.
  -w workflow_file, --workflow workflow_file
                        Path to workflow file.
  --dart_command dart_command
                        Command to invoke DART Runner.
  --overwrite, --no-overwrite
                        Overwrite duplicate bags. (default: False)
  --dry-run, --dryrun   Log execution steps without actually executing. (default: False)
```

ReBACH-Bagger can also be imported as a module. The `main.py` script
contains an example of what this looks like in practice, but a simplified
example follows:

```python
# Import Bagger
from bagger.bag import Bagger

# Instantiate Bagger with necessary arguments
B = Bagger(workflow, archival_staging_storage, delete, dart_command, config, log)

# Run DART on the package specified with path
run = B.run_dart(path)
```

### Return Values

ReBACH-Bagger's return values are defined in the `Status` object in `bagger/__init__.py`:

```python
class Status(IntEnum):
    SUCCESS = 0
    ERROR = 1
    INVALID_PATH = 2
    DUPLICATE_BAG = 3
    INVALID_PACKAGE = 4
    WASABI_ERROR = 5
    INVALID_CONFIG = 6
    DRY_RUN = SUCCESS
```

Code that imports the `Bagger` module can use the name or value of the `Status` object:

```python
if status == Status.INVALID_PATH:
    print("Try a different path")

if status > 0:
    print("Bag not created")
```

Scripts can pass the value of the `Status` object as an exit code which the calling program may
use to decide whether to exit or retry:

```python
if error:
    raise SystemExit(Status.WASABI_ERROR)
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
configuration options are first in precedence, meaning values passed with the
command line will override values set in the config file.

```toml
[Defaults]
archival_staging_storage = "out" # DART will output generated bags here; must be writable
workflow = "default_workflow.json" # Path to the DART workflow file
dart_command = "dart-runner" # Command or path to DART executable
```

There are currently two workflows `default_workflow.json` and `noupload_workflow.json`. The only difference is that the latter instructs dart-runner to not upload files to any remote storage locations.

### Logging

ReBACH-Bagger logs errors, debug messages, and DART output to disk.

```toml
[Logging]
log_dir = "logs" # Logger will write logs to this directory
logfile_prefix = "ReBACH-Bagger" # Log filename prefix
```

### AP Trust

Neither ReBACH-Bagger nor Dart uploads to AP Trust directly but like ReBACH, Bagger also checks AP Trust for duplicate bags when workflow does not include upload settings. 
The configuration and credentials in this section are used to authenticate and check AP Trust for duplicate bags.

```toml
[aptrust_api]
url = "***override***" # required: The AP Trust member API url including the version
user = "***override***" # required: Your user email address on AP Trust
token = "***override***" # required: Your user secret token on AP Trust
items_per_page = "***override***" # Maximum number of object to be return per page by the API
alt_identifier_starts_with = "***override***" # Prefix for alternate identifier in AP Trust
retries = 3 # required: Number of times the script should retry API or file system calls if it is unable to connect. Defaults to 3
retries_wait = 10 # required: Number of seconds the script should wait between call retries if it is unable to connect. Defaults to 10
```

### Wasabi

Both DART and ReBACH-Bagger use the credentials in this section to authenticate to Wasabi.
ReBACH-Bagger checks Wasabi for duplicate bags when the DART workflow is configured to upload to 
remote storage location or when the `--check-remote-staging` flag is set by ReBACH. See [DART Workflow](#dart-workflow) for details on how these variables are used in DART.

If the `dart_workflow_hostbucket_override` variable is set to `true`
(default), the values of `host` and `bucket` defined here are used in the DART workflow defined in the
`workflow` variable above. If set to `false`, the values defined in the workflow itself are used instead. This
option can only be set in the configuration file.

```toml
[Wasabi]
name = "***override***"
host = "***override***"
bucket = "***override***"
host_bucket = "***override***"
access_key = "***override***"
secret_key = "***override***"
dart_workflow_hostbucket_override = true
```

## Metadata Configuration

ReBACH-Bagger can apply a configurable set of metadata tags to the bags it generates. These tags
are defined in the `Metadata` section of the configuration file. The tags are defined with the
following schema:

`# tag-file.Tag-Name = "Tag value"`

The `tag-file` element corresponds to the tag file (e.g. "bag-info.txt") in which the tag will be
placed. Do not include `.txt` as part of the tag-file element.

`Tag-Name` is the name of the metadata tag. Conventionally, tag names are uppercase, dash-separated
words.

The `"Tag value"` element can be a string or an inline table ([see below]("#metadata-from-json")).
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
bag-info.First-Author = { tag_path = ["authors.0.full_name"] }
bag-info.License = { tag_path = ["license.name"] }
bag-info.DOI = { tag_path = ["doi"] }
```

To extract multiple items and concatenate their values into a single tag, include more list items.

```toml
bag-info.External-Identifier = { tag_path = ["authors.0.full_name", "#hash#"] }
```

Note the special value `#hash#`. This will not extract values from the JSON but instead from the name of the bag that will be created. Available values:

- `#id#`: The article id
- `#version#`: The article version (in `vXX` format where XX is a zero-padded number from 1 to 99)
- `#hash#`: The metadata hash
- `#bag_count#`: The bag count
- `#last_name#`: The last name of the first author

In the example, the value of External-Identifier will be set to `Brian Avants-<md5>` where `<md5>` is the 32 character MD5 hash computed by bagger for the bag name. To include literal text in the tag, enclose it in `@`. 

```toml
bag-info.External-Identifier = { tag_path = ["@azu_@", "authors.0.full_name", "#hash#"] }
```
sets External-Identifier to `azu_Brian Avants-<md5>`


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

A [DART workflow](https://aptrust.github.io/dart-docs/users/workflows/) can be represented as a JSON file that
describes the packaging and upload operations which should be performed when a bag is created by
DART Runner. Users should create the workflow file using the desktop version of DART. Details
are available in the [DART documentation](https://aptrust.github.io/dart-docs/users/workflows/).

The workflow file will include a name, description, the package format (BagIt) and a BagIt
profile (APTrust or a profile based on APTrust containing additional ReDATA-specific tags;
[see below]("#bagit-profile")). The workflow will also include the storage location and credentials
needed to upload the bag.

When creating a new workflow with DART, users should NOT enter their AWS/Wasabi access key or
secret key into the workflow configuration. Instead, DART provides the option to access these
values [with an environment variable](https://aptrust.github.io/dart-docs/users/settings/storage_services/#login),
which ReBACH-Bagger will populate from the Wasabi credentials in the configuration file.

Instead of entering the access key ID into the login field, enter `env:WASABI_ACCESS_KEY_ID`.
For the password, enter `env:WASABI_SECRET_ACCESS_KEY`.

### BagIt Profile

The BagIt profile describes the metadata tags that are required or expected to be stored within
the bag. These tags include default tags common to all BagIt bags, tags required by APTrust, and
tags defined by the ReBACH-Bagger metadata configuration ([see above]("#metadata-from-json")).
Profiles can be created and modified [using DART's desktop application](https://aptrust.github.io/dart-docs/users/bagit/).
Profiles are embedded in the DART workflow file and do not need to be separately provided to
ReBACH-Bagger.

### Execution Notes

1. **Definition of “Preserved” Bag**  
   - A bag is considered preserved if it is in:  
     - Archival staging storage **and/or** archival storage  
     - S3 storage **if** the Dart workflow JSON includes the *storage services* setting  

2. **Default Storage Behavior**  
   - By default, ReBACH with Bagger using the Dart workflow JSON stores bags in **archival staging storage**  

3. **Uploading to S3 Storage**  
   - Possible **only if** the Dart workflow JSON includes the *storage services* setting  

4. **Archival Storage Uploads**  
   - ReBACH and Bagger **do not** upload bags to archival storage  
   - They can check for duplicate bags in **all** storage locations, including archival storage  

5. **Duplicate Bag Checking in S3**  
   - Controlled by the `--check-remote-staging` flag in ReBACH  
   - **Regardless of the flag**, S3 will be checked for duplicates if Dart workflow JSON is configured to upload to S3.  

6. **Handling of Duplicate Bags**  
   - If a duplicate bag exists in a storage location:  
     - The item is **not processed**  
     - No bag is generated for that item 

7. **Key Determinant for Skipping Processing**  
   - The storage services setting in the Dart workflow JSON dictates whether Dart uploads to S3 and thus affects duplicate checking behavior  

8. **Storage Location Summary**  
   - All bags go into archival staging storage by default  
   - They are later ingested into archival storage by UAL’s preservation workflow  
   - Bags in archival staging storage are presumed to also be in archival storage

The table below summarizes how bags are placed in different storages.

| **Bag in Archival staging storage/Archival storage** | **Upload bag to S3 storage** | **Bag in S3 storage** | **Process bag** | **Bag location after run**                |
|------------------------------------------------------|------------------------------|-----------------------|-----------------|-------------------------------------------|
| No                                                   | No                           | No                    | Yes             | Archival staging storage/Archival storage |
| No                                                   | No                           | Yes                   | Yes             | All storages                              |
| No                                                   | Yes                          | No                    | Yes             | All storages                              |
| No                                                   | Yes                          | Yes                   | No              | All storages                              | 
| Yes                                                  | No                           | No                    | No              | Archival staging storage/Archival storage | 
| Yes                                                  | No                           | Yes                   | No              | All storages                              | 
| Yes                                                  | Yes                          | No                    | Yes             | All storages                              |
| Yes                                                  | Yes                          | Yes                   | No              | All storages                              |  
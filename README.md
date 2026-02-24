# ReBACH

## Purpose
This Python tool enumerates all the items and collections in ReDATA, downloads the associated files and metadata into a predefined structure on ingest staging storage, gathers curation information from curation storage, and adds the gathered information to the predefined structure.

## Description
ReBACH is run via the command line as outlined in the 'How to Run' section of this readme. During its run, ReBACH enumerates all published items and their versions on UArizona's Figshare using the Figshare API and downloads their metadata to the system memory. ReBACH then downloads files into the ingest staging storage for items that have a matching curation storage folder. The tool then validates the files and folder structure in the curation storage for those items. For the items that have matching folders in the curation storage that pass validation, ReBACH copies the files from the curation storage into the corresponding ingest staging storage folder, otherwise the ingest staging storage folder and its contents are deleted. Information and errors are logged in a file with some information and errors displayed in the terminal.

## Dependencies
- Python 3.14
- Ubuntu >= 22.04
- redata >= 0.6.1
- s3cmd >= 2.4.0
- tomli >= 2.4.0
- python-slugify >= 8.0.4

## Requirements
- Figshare organization number
- Figshare API token for respective organization
- Archival storage (AP Trust) user email
- Archival storage (AP Trust) user secret
- Read privileges to curation storage location
- Write privileges to ingest staging storage and archival staging storage
- Write privileges to logs location

## Installation Instructions

#### Python and setting up a `mamba` environment

First, install a working version of Python (>=3.14).  We recommend using the [Mamba](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html) package installer.
Mamba is a drop-in replacement for Anaconda and you will be able to use `conda` commands in an environment created with `mamba`. After installing Mamba, set `conda-forge` as the default channel to fetch packages. Run the following commands to set `conda-forge` as the default channel and remove Ananconda channels.

Add conda-forge to your channels: 

`conda config --add channels conda-forge`

Set strict channel priority: 

`conda config --set channel_priority strict`

Remove Anaconda channels: 

`conda config --remove channels defaults`

After you have installed and configured Mamba, you will want to create a separate `mamba` environment and activate it:

```
$ mamba create -n rebach python=3.14
$ mamba activate rebach
```

With the activated `mamba` environment, next clone [this repository (ReBACH)](https://github.com/UAL-RE/ReBACH) . Ensure the user has read and write permissions to the cloned folder and install the dependencies with following commands:

```
(rebach) $ cd /path/to/cloned/rebach/folder
(rebach) $ pip install -r requirements.txt
```


## How to run
- Copy the .env.sample.ini file and give it a name of your choice (e.g. .env.ini).
- Fill out the .env.ini file (IMPORTANT: Make sure not to commit this file to Github)
    - figshare_api
	    - url - required: The figshare API url
	    - token - required: Your auth token to your organization's API
	    - retries - required: Number of times the script should retry API or file system calls if it is unable to connect. Defaults to 3.
	    - retries_wait - required: Number of seconds the script should wait between call retries if it is unable to connect. Defaults to 10.
	    - institution - required: The Figshare Institution ID for your organization.
    - ingest_staging_storage - required: The file system location where the preservation folders/packages should be created for ingest into UAL's preservation workflow. Ensure this location is different from archival_staging_storage location in `bagger/config/default.toml`.
    - logs_location - required: The file system location where logs should be created. This value will override the one in `bagger/config/default.toml` when bagger is used for post-processing (see post_process_script_command setting below).
    - additional_percentage_required - required: How much extra space the `ingest_staging_storage` should have in order to handle files as a percent. This percent is applied to the total storage needed for all files. I.e. if the value of this field is 10 and the amount of storage needed for files is 1 GB, the script will make sure that the `ingest_staging_storage` has at least 1.1 GB free. Defaults to 10.
    - pre_process_script_command - optional: The terminal command (including arguments) to invoke a script to be run BEFORE the files are copied and logic applied to the `ingest_staging_storage` (note: this action is not currently implemented).
    - post_process_script_command - required: Specifies the method of performing post-processing steps. This can take only two values: the string 'Bagger', or the path to an external script. If the value is set to 'Bagger', the post-processing steps will consist of running the internal `bagger` module. If the value is set to a path to an external script, the post-processing steps will be executed by invoking the external script through the function 'post_process_script_function'. The post-processing steps are executed AFTER the files are copied and logic applied to the `ingest_staging_storage`.
    - curation_storage_location - required: The file system location where the curation files reside.
    - bag_name_prefix - required: This is the prefix for bag names. It is the first set of characters before the underscore("_") that precedes the article_id in bag name, and it defaults to "azu" in env.ini file if not changed.
- Ensure the aforementioned Dependencies and Requirements are met.
- Navigate to the root directory of ReBACH via the terminal and start the script by entering the command `python3 app.py --xfg /path/of/.env.ini` or `python app.py --xfg /path/of/.env.ini` depending on your system configuration (note: the script must be run using Python 3.9 or greater).
- Informational and error output will occur in the terminal. The same output will be appended to a file in the logs location with today's date with some additional information and error logging occurring in the file. The log details are described in [Description of ReBACH Log Messages](ReBACH_Logs_Summary_Description.md).  
- Final preservation package output will occur in the `ingest_staging_storage` you specified in the env.ini file.

## Command line
These parameters are only available on the command line.
|Parameter| Description |
|---------|-------------|
|`--xfg`  | The path to the configuration file to use. |
|`--ids`  | A comma-separated list of article IDs to process. E.g., 12345,12356. |
|`--continue-on-error`| If there is an error during the item processing stage for a given item, skip it and continue to the next item. |
|`--dry-run` | Runs all operations, excluding any that involve writing any storage medium. |
|`--check-remote-staging` | Checks alternative remote staging storage for duplicate bags.  |

## Execution notes
- ReBACH will attempt to fetch all items in the institutional instance. Items that are not published (curation_status != 'approved') will be ignored.
- Items that are embargoed are also fetched however due to limitations in the API, only the latest version can be fetched until the embargo expires or is removed.
- While fetching, ReBACH checks `archival_staging_storage` in `bagger/config/default.toml` and `archival storage` for a duplicate bags of each item. If a duplicate of an item is found and confirmed in any of the locations, the item will ignored in subsequent stages except when Bagger's Dart workflow json file is configured to upload to a S3 storage.
- Checking archival storage for a duplicate bags of an article requires size of the curation storage folder of the article. If an error occurs while calculating the size of an article curation folder, the error will be recorded and execution will stop except if the `--continue-on-error` flag is set.
- Remote archival staging storage will be checked for duplicate bags if DART workflow json file configured to upload to an S3 storage, even if the `--check-remote-staging` flag is not set.
- When processing collections, ReBACH records which items are part of the collection by appending them to collection's JSON as returned by the Figshare API.
- If an item encounters errors, it will not be processed and any partial files are deleted in ingest staging storage.

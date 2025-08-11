# ReBACH

## Purpose:
This Python tool enumerates all the items and collections in ReDATA, downloads the associated files and metadata into a predefined structure on preservation staging storage, gathers curation information from curation staging storage, and adds the gathered information to the predefined structure.

## Description:
ReBACH is run via the command line as outlined in the 'How to Run' section of this readme. During its run, ReBACH enumerates all published items and their versions on UArizona's Figshare using the Figshare API and downloads their metadata to the system memory. ReBACH then downloads files into the preservation staging storage for items that have a matching curation staging storage folder. The tool then validates the files and folder structure in the curation staging store for those items. For the items that have matching folders in the curation staging storage that pass validation, ReBACH copies the files from the curation staging storage into the corresponding preservation staging storage folder, otherwise the preservation staging storage folder and its contents are deleted. Information and errors are logged in a file with some information and errors displayed in the terminal.

## Dependencies:
- Python >= 3.9
- requests Python library >= 2.18.4
- Ubuntu >= 20.04
- Slugify >= 7.0.0

## Requirements:
- Figshare organization number
- Figshare API token for respective organization
- Preservation final remote storage (AP Trust) user email
- Preservation final remote storage (AP Trust) user secret
- Read privileges to Curation storage location
- Write privileges to Preservation storage location
- Write privileges to logs location

## How to run:
- Copy the .env.sample.ini file and give it a name of your choice (e.g. .env.ini).
- Fill out the .env.ini file (IMPORTANT: Make sure not to commit this file to Github)
    - figshare_api
	    - url - required: The figshare API url
	    - token - required: Your auth token to your organization's API
	    - retries - required: Number of times the script should retry API or file system calls if it is unable to connect. Defaults to 3
	    - retries_wait - required: Number of seconds the script should wait between call retries if it is unable to connect. Defaults to 10
	    - institution - required: The Figshare Institution ID for your organization
    - ingest_staging_storage - required: The file system location where the preservation folders/packages should be created
    - logs_location - required: The file system location where logs should be created. This value will override the one in `bagger/config/default.toml` when bagger is used for post-processing (see post_process_script_command setting below).
    - additional_percentage_required - required: How much extra space the preservation storage location should have in order to handle files as a percent. This percent is applied to the total storage needed for all files. I.e. if the value of this field is 10 and the amount of storage needed for files is 1 GB, the script will make sure that the preservation storage location has at least 1.1 GB free. Defaults to 10
    - pre_process_script_command - optional: The terminal command (including arguments) to invoke a script to be run BEFORE the files are copied and logic applied to the preservation storage (note: this action is not currently implemented)
    - post_process_script_command - required: Specifies the method of performing post-processing steps. This can take only two values: the string 'Bagger', or the path to an external script. If the value is set to 'Bagger', the post-processing steps will consist of running the internal `bagger` module. If the value is set to a path to an external script, the post-processing steps will be executed by invoking the external script through the function 'post_process_script_function'. The post-processing steps are executed AFTER the files are copied and logic applied to the preservation storage.
    - curation_storage_location - required: The file system location where the Curation files reside
    - bag_name_prefix - required: This is the prefix for bag names. It is the first set of characters before the underscore("_") that precedes the article_id in bag name, and it defaults to "azu" in env.ini file if not changed.   
- Ensure the aforementioned Dependencies and Requirements are met
- Navigate to the root directory of ReBACH via the terminal and start the script by entering the command `python3 app.py --xfg /path/of/.env.ini` or `python app.py --xfg /path/of/.env.ini` depending on your system configuration (note: the script must be run using Python 3.9 or greater)
- Informational and error output will occur in the terminal. The same output will be appended to a file in the logs location with today's date with some additional information and error logging occurring in the file. The log details are described in [Description of ReBACH Log Messages](ReBACH_Logs_Summary_Description.md).  
- Final preservation package output will occur in the preservation location you specified in the env.ini file

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
- While fetching, ReBACH checks preservation remote storages for a preserved copy of each item. If a preservation copy of an item is found and confirmed, the item will ignored in subsequent stages.
- Checking preservation final remote storage for a preserved copy of an article requires size of the curation storage folder of the article. If an error occurs while calculating the size of an article curation folder, the error will be recorded and execution will stop except if the `--continue-on-error` flag is set.
- Remote staging storage will be checked for duplicate bags if workflow is set to upload, even if the `--check-remote-staging` flag is not set.
- When processing collections, ReBACH records which items are part of the collection by appending them to collection's JSON as returned by the Figshare API.
- If an item encounters errors, it will not be processed and any partial files are deleted in preservation staging storage.

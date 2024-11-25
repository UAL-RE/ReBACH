# Changelog


## [v1.0.0](https://github.com/UAL-RE/ReQUIAM/tree/v1.0.0)
Initial version

## What's Changed

### Features
* Add validation for preservation directory struct. in https://github.com/UAL-RE/ReBACH/pull/3
* Check curation_folder_access for readonly vs readwrite in https://github.com/UAL-RE/ReBACH/pull/26
* Chunk downloads and add more log messages in https://github.com/UAL-RE/ReBACH/pull/29
* Chunk the hash check in Article.py in https://github.com/UAL-RE/ReBACH/pull/32
* Add warning message for articles without a curation folder in https://github.com/UAL-RE/ReBACH/pull/39
* Add validations for ‘post-processing script’ parameter in configuration file in https://github.com/UAL-RE/ReBACH/pull/40
* Allow overriding of Wasabi credentials in DART workflow (Issue #47) in https://github.com/UAL-RE/ReBACH/pull/50
* Case insensitive filename comparisons (Issue #57) in https://github.com/UAL-RE/ReBACH/pull/58
* Add color to messages in the console (Issue #62) in https://github.com/UAL-RE/ReBACH/pull/65
* Keep track of items successfully processed (Issue #66) in https://github.com/UAL-RE/ReBACH/pull/75
* Update BagIt profiles and associated workflows (Issue #73) in https://github.com/UAL-RE/ReBACH/pull/76
* enhance log messages in certain cases (Issue #80) in https://github.com/UAL-RE/ReBACH/pull/82
* add option to continue item processing on error (Issue #86) in https://github.com/UAL-RE/ReBACH/pull/87
* Improve Bagit profiles for APTrust (Issue #94) in https://github.com/UAL-RE/ReBACH/pull/95
* Improve summary messages (Issue #97) in https://github.com/UAL-RE/ReBACH/pull/98
* Fix free disk space needs computation (Issue #96) in https://github.com/UAL-RE/ReBACH/pull/99
* Check if item version is already preserved before bagging (Issue #102) in https://github.com/UAL-RE/ReBACH/pull/103
* Implement `--dry-run` flag in https://github.com/UAL-RE/ReBACH/pull/106

### Bug fixes
* Change the regexes to be more flexible on article_id and version in https://github.com/UAL-RE/ReBACH/pull/7
* Make curation validation less strict in https://github.com/UAL-RE/ReBACH/pull/10
* Incorrect metadata directory and filename in https://github.com/UAL-RE/ReBACH/pull/37
* Missing first_depositor_full_name in preservation storage folder creation in https://github.com/UAL-RE/ReBACH/pull/38
* Bagging log message consistency and location in main app (Issue #51) in https://github.com/UAL-RE/ReBACH/pull/52
* Bags uploaded despite error (Issue #60) in https://github.com/UAL-RE/ReBACH/pull/63
* Add missing option to bagger config (Issue #69) in https://github.com/UAL-RE/ReBACH/pull/70
* Crash when not uploading bags (Issue #71) in https://github.com/UAL-RE/ReBACH/pull/72
* Add retries to file downloading (Issue #81) in https://github.com/UAL-RE/ReBACH/pull/83
* Properly count articles that are published vs unpublished (Issue #79) in https://github.com/UAL-RE/ReBACH/pull/84
* Incorrect bag is processed (Issue #89) in https://github.com/UAL-RE/ReBACH/pull/90
* Avoid various error conditions with collections (Issue #91) in https://github.com/UAL-RE/ReBACH/pull/92
* Fix: Write Internal-Sender-Identifier to bags (Issue #100) in https://github.com/UAL-RE/ReBACH/pull/101
* Fix: Preprocessing of articles stops if curation folder does not exist for an article (Issue #105) in https://github.com/UAL-RE/ReBACH/pull/107
* Fix: Preservation package check fails when multiple copies of an item are already preserved (Issue 108) in https://github.com/UAL-RE/ReBACH/pull/109

### Others
* Org rename in https://github.com/UAL-RE/ReBACH/pull/2
* Change process in https://github.com/UAL-RE/ReBACH/pull/9
* Client feedback 1 in https://github.com/UAL-RE/ReBACH/pull/11
* Merge ReBACH-Bagger in https://github.com/UAL-RE/ReBACH/pull/13
* Logging changes in app.py in https://github.com/UAL-RE/ReBACH/pull/14
* README updates in https://github.com/UAL-RE/ReBACH/pull/15
* Address the issue #17 in https://github.com/UAL-RE/ReBACH/pull/21
* Address the issue #22 - Implemented method 'post_proces_script_function' with parameters in https://github.com/UAL-RE/ReBACH/pull/24
* Address Issue 43 - Enhance ReBACH to accept specific article and collection IDs for selective processing in https://github.com/UAL-RE/ReBACH/pull/44
* Address Issue 27 - Selective processing and uploading of articles and collections mentioned in the command-line argument in https://github.com/UAL-RE/ReBACH/pull/45
* Update setup.py with various fixes in https://github.com/UAL-RE/ReBACH/pull/53

## Contributors
* @astrochun 
* @zoidy 
* @davidagud 
* @jonathannoah 
* @rubab 
* @HafeezOJ 


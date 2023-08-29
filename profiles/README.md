# BagIt Profile
This profile is used by ReBACH to generate bags. There are two versions of the profile

- BagIt Profile Specification format v1.3.0, `redata-bagit-vxx.json`. This is the standards-compliant version.
- DART format. `redata-bagit-dart-vxx.json`. This is the version actually used by ReBACH (directly embedded in the workflow files in the config directory).

The DART version contains additional information that isn't supported by the BagIt Profile Specification such as help text for the DART GUI. Additionally, from the DART documentation: "note that this format [BagIt Profile Specification] cannot describe information about required tags outside of the bag-info.txt file."
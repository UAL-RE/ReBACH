# BagIt Profile

This profile is used by ReBACH bagger to generate bags. The profile is in the DART format instead of the BagIt Profile Specification Format as the former is a superset of the latter and can be more easily used in our dart-runner workflow. One notable deficiency in the official specification is that "note that this format cannot describe information about required tags outside of the bag-info.txt file." Refer to the [DART BagIt documentation](https://aptrust.github.io/dart-docs/users/bagit/) for details.

## Implementation Conventions

- The format of the file is a DART settings JSON object. The profile itself is contained within the `bagItProfiles` key.
- Each profile is versioned as indicated in the file name and in the `bagItProfileInfo.version` value.
- Prior versions will remain available for checking bags generated with that version.

## Profile Creation

To create a profile from scratch, start with the DART GUI.

- Create a new profile from scratch or by cloning an existing one
- Create a new storage to be used to upload bags to. E.g., Wasabi (optional)
- Export the settings via the Settings -> Export Settings menu. Check only the profile and storage created above. Uncheck any items in the App Settings section
- Save the JSON into a file named `redata-bagit-dart-vXX.json` where XX is the version.

## Profile Updates

Profiles can be updated by manually editing the JSON or by importing the `redata-bagit-dart-vXX.json` into DART, editing as needed, and re-exporting.


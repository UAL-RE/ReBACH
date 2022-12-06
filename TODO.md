# ReDATA DART Preservation Tool

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust DART tool, and uploading the completed bag to offsite storage.

### Configuration

- [ ] Add and test configuration variables for overwrite and delete

### Testing

- [x] Generate test data from sample data
- [x] Scaffold tests
- [x] Test Wasabi storage (connectivity, etc)
    - Get more data from s3cmd to log if there are errors
- [ ] Handle errors if DART doesn't execute

### Metadata Integration

- [x] Construct metadata tags from metadata file
- [ ] Add optional metadata elements (author)
- [x] Make set of extracted metadata and mappings to bag tags configurable

### Logging

- [x] Log all specified activities with redata.commons logging util

### Deployment

- [ ] Merge with ReBACH repo.
- [ ] Rename to rebach_bagger

- If dart-runner not found, print message and point user to where to locate it
    - Do not attempt to download it
    - Add to documentation: how to download, where to put, how to set
      executable
      permission



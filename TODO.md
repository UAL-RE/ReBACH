# ReDATA DART Preservation Tool

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust DART tool, and uploading the completed bag to offsite storage.

### Testing

- [x] Generate test data from sample data
- [ ] Scaffold tests

### Metadata Integration

- [ ] Construct metadata tags from metadata file
- [ ] Add optional metadata elements (author)
- [ ] Make set of extracted metadata and mappings to bag tags configurable

### Logging

- [x] Log all specified activities with redata.commons logging util

### Deployment

- If dart-runner not found, print message and point user to where to locate it
    - Do not attempt to download it
    - Add to documentation: how to download, where to put, how to set executable
      permission

- Handle errors if DART doesn't execute
# ReBACH-Bagger

This tool implements the "last mile" of ReDATA's preservation strategy by
ingesting a data/metadata package, generating a preservation-ready bag using
the APTrust DART tool, and uploading the completed bag to offsite storage.

## Usage

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

## Configuration

ReBACH-Bagger uses [TOML-based](https://toml.io/en/) configuration files found
in the config directory. The `default.example.toml` file in the config
directory contains the configuration keys expected by ReBACH-Bagger.

### Metadata Configuration

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
bag-info.First-Author = "authors.0.full_name"
bag-info.License = "license.name"
bag-info.DOI = "doi"
```


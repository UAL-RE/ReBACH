import json
import textwrap
from collections import namedtuple
from logging import Logger
from pathlib import Path
from typing import Literal, Union

from bagger.strip import strip_tags

Tag = namedtuple('Tag', ['tag_file', 'tag_name', 'tag_value'])


class Metadata:

    def __init__(self, config: dict, metadata_json_path: Path, log: Logger):
        self.config: dict = config
        self.log: Logger = log
        self.metadata_json_path: Path = metadata_json_path
        self.metadata_config: dict = self.config['Metadata']

        self.tags: list[Tag] = []

        with open(self.metadata_json_path, 'r') as f:
            self.data: dict = json.load(f)

    def parse_metadata(self) -> Union[list[Tag], Literal[False]]:
        strip_html = False
        shorten = False

        for _tag_file, tags in self.metadata_config.items():
            tag_file = f'{_tag_file}.txt'
            for tag_name, tag_annotation in tags.items():
                if isinstance(tag_annotation, dict):
                    # If the tag_annotation in metadata config is a dict, we need to get the
                    # `tag_source` and check for `html_strip` and `shorten` options
                    try:
                        tag_source = tag_annotation['tag_source']
                    except KeyError:
                        self.log.error(f"Metadata key '{_tag_file}.{tag_name}' "
                                       f"must have tag_source defined")
                        return False
                    strip_html = tag_annotation.get('strip_html', False)
                    shorten = tag_annotation.get('shorten', False)

                else:
                    # If the tag_annotation is not a dict, use it as the source
                    tag_source = tag_annotation
                split_tag_source = tag_source.split('.')

                tag_value = self._descend_json(self.data, split_tag_source)

                if not tag_value:
                    return False

                if strip_html:
                    tag_value = strip_tags(tag_value)

                if shorten:
                    tag_value = textwrap.shorten(tag_value, shorten)

                self.tags.append(Tag(tag_file, tag_name, tag_value))

        return self.tags

    def _descend_json(self, metadata: dict, tag_source: list) -> Union[str, Literal[False]]:
        if len(tag_source) == 1:
            try:
                return metadata[tag_source[0]]
            except KeyError as e:
                self.log.error(f"Key '{e.args[0]}' not found in metadata "
                               f"JSON file.")
                return False

        else:
            return self._descend_json(metadata[tag_source[0]], tag_source[1:])

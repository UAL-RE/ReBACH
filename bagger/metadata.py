import json

from collections import namedtuple
from logging import Logger
from pathlib import Path
from typing import Literal, Union

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
        for tag_file, tags in self.metadata_config.items():
            tag_file = f'{tag_file}.txt'
            for tag_name, tag_source in tags.items():
                split_tag_source = tag_source.split('.')
                tag_value = self._descend_json(self.data, split_tag_source)

                if not tag_value:
                    return False

                self.tags.append(Tag(tag_file, tag_name, tag_value))

        return self.tags

    def _descend_json(self, metadata: dict, tag_source: list) -> bool:
        if len(tag_source) == 1:
            try:
                return metadata[tag_source[0]]
            except KeyError as e:
                self.log.error(f"Key '{e.args[0]}' not found in metadata "
                               f"JSON file.")
                return False

        else:
            return self._descend_json(metadata[tag_source[0]], tag_source[1:])

import json
import textwrap
from collections import namedtuple
from logging import Logger
from pathlib import Path
from typing import Literal, Union

from bagger.strip import strip_tags

Tag = namedtuple('Tag', ['tag_file', 'tag_name', 'tag_value'])


class Metadata:

    def __init__(self, config: dict, metadata_json_path: Path, article_id: str, version: str, ver_hash: str, log: Logger):
        """
        Assemble metadata tags to embed in bags

        :param config: Config dict
        :param metadata_json_path: Path to package metadata JSON file
        :param article_id: id of the article being processed
        :param version: version of the article_id being processed
        :param hash: identifying hash of the item being processed
        :param log: Logger object
        """
        self.config: dict = config
        self.log: Logger = log
        self.metadata_json_path: Path = metadata_json_path
        self.metadata_config: dict = self.config['Metadata']
        self.article_id: str = article_id
        self.version: str = version
        self.hash: str = ver_hash

        self.tags: list[Tag] = []

        with open(self.metadata_json_path, 'r') as f:
            self.data: dict = json.load(f)

    def parse_metadata(self) -> Union[list[Tag], Literal[False]]:
        """
        Retrieve metadata values from the metadata JSON file

        :return: List of Tags: [(tag file, tag name, tag value)]
        """
        strip_html = False
        shorten = False

        for _tag_file, tags in self.metadata_config.items():
            tag_file = f'{_tag_file}.txt'
            for tag_name, tag_annotation in tags.items():

                # If the tag_annotation in metadata config is not a dict, the tag value is the
                # tag annotation:
                if not isinstance(tag_annotation, dict):
                    self.tags.append(Tag(tag_file, tag_name, tag_annotation))
                    continue

                # Otherwise, the tag_value needs to be extracted from the metadata, and we need to
                # check for strip_html and shorten.
                try:
                    tag_path_list = tag_annotation['tag_path']
                except KeyError:
                    self.log.error(f"Metadata key '{_tag_file}.{tag_name}' "
                                   f"must have tag_path defined")
                    return False

                strip_html = tag_annotation.get('strip_html', False)
                shorten = tag_annotation.get('shorten', False)
                tag_value_sep = '-'
                tag_value_list =[]
                for tag_path in tag_path_list:
                    if tag_path.startswith('#') and tag_path.endswith('#'):
                        # Special case where we want to use article_id, version, or hash in tag files
                        try:
                            tag_value_list.append(getattr(self, tag_path.replace('#','')))
                        except AttributeError:
                            print(f"Error: Variable '{tag_path.replace('#','')}' does not exist in class Metadata.")
                    else:
                        split_tag_path = tag_path.split('.')

                        tag_value = self._descend_json(self.data, split_tag_path, tag_path)

                        if not tag_value:
                            tag_value_list.append("")
                        else:
                            if strip_html:
                                tag_value = strip_tags(tag_value)

                            if shorten:
                                tag_value = textwrap.shorten(tag_value, shorten)

                            tag_value_list.append(str(tag_value))

                self.tags.append(Tag(tag_file, tag_name, tag_value_sep.join(tag_value_list)))

        return self.tags

    def _descend_json(self, metadata: dict, tag_path: list,
                      original_tag_path: str) -> Union[str, Literal[False]]:
        """
        Recursively extract JSON using the dot-separated tag_paths as keys

        :param metadata: Metadata file or portion
        :param tag_path: Tag path or portion
        :param original_tag_path: Original complete tag path
        :return: Metadata value from package metadata file
        """

        # If there is only one tag_path element, extract the equivalent key from the metadata
        if len(tag_path) == 1:
            try:
                return metadata[tag_path[0]]
            except KeyError as e:
                self.log.error(f"Key '{e.args[0]}' not found in metadata JSON file.")
                return False

        # If tag_path returns a list from metadata, try to use next tag_path element as the index
        if isinstance(metadata[tag_path[0]], list):
            if tag_path[1].isdigit():
                index = int(tag_path[1])
                return self._descend_json(metadata[tag_path[0]][index], tag_path[2:],
                                          original_tag_path)
            else:
                self.log.error(
                    f"The tag_path '{original_tag_path}' is invalid. The path element "
                    f"'{tag_path[0]}' returns a list, but the following path element "
                    f"'{tag_path[1]}' is not an integer.")
                return False

        # If there are non-list tag_path elements remaining, continue extracting the metadata
        else:
            return self._descend_json(metadata[tag_path[0]], tag_path[1:], original_tag_path)

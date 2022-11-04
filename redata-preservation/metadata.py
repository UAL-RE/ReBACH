import json

from os import path
from typing import Tuple


def __decompose_name(package_name: str) -> Tuple:
    # Format of preservation package name:
    # [article_id]_[version]_[first_depositor_full_name]_[metadata_hash]

    path_elements = package_name.split('_')

    article_id = path_elements[0]
    version = path_elements[1]
    metadata_hash = path_elements[-1]

    return article_id, version, metadata_hash


def get_metadata(package_path: str) -> dict:
    # Get package name (directory name) from path if a subdir is involved
    package_name = path.basename(path.normpath(package_path))

    article_id, version, metadata_hash = __decompose_name(package_name)

    metadata_dir = f'v{version}/METADATA/'
    metadata_filename = f'preservation_final_{article_id}.json'

    full_path = path.join(package_path, metadata_dir, metadata_filename)

    with open(full_path, 'r') as f:
        data = json.load(f)

    metadata = dict()
    metadata['title'] = data['title']
    metadata['doi'] = data['doi']
    metadata['published_date'] = data['published_date']
    metadata['license'] = data['license']['name']

    return metadata

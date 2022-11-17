import json


def get_metadata(metadata_path: str) -> dict:
    """
    Pull metadata from preservation package JSON file.

    :param metadata_path: Path to preservation package metadata JSON file
    :return: Dict with required metadata elements
    """

    with open(metadata_path, 'r') as f:
        data = json.load(f)

    metadata = dict()
    metadata['title'] = data['title']
    metadata['doi'] = data['doi']
    metadata['published_date'] = data['published_date']
    metadata['license'] = data['license']['name']

    return metadata

import json

from os import path


def __decompose_name(package_name: str) -> tuple[str, str, str]:
    """
    Decompose the name of a package into parts to enable parsing the package
    :param package_name: Name (directory) of package
    :return: Tuple of package name parts
    """
    # Format of preservation package name:
    # [article_id]_[version]_[first_depositor_full_name]_[metadata_hash]

    path_elements = package_name.split('_')

    # Article ID and version are the first and second elements
    article_id = path_elements[0]
    version = path_elements[1]
    # Depositor can be arbitrary number of elements because it is snake-cased,
    # so get hash as last element
    metadata_hash = path_elements[-1]

    return article_id, version, metadata_hash


def get_metadata(package_path: str) -> dict:
    """
    Pull metadata from package preservation_final JSON file.
    :param package_path: Path to the package
    :return: Dict with required metadata elements
    """
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

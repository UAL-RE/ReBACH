from pathlib import Path


def get_commit(repo_path):
    # https://stackoverflow.com/a/68215738
    git_folder = Path(repo_path, '.git')
    head_name = Path(git_folder, 'HEAD').read_text().split('\n')[0].split(' ')[-1]
    head_ref = Path(git_folder, head_name)
    commit = head_ref.read_text().replace('\n', '')
    return commit


__commit__ = get_commit('.')
__version__ = '1.0.1'

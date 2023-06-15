from setuptools import setup

with open("bagger/README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fr:
    requirements = fr.read().splitlines()

setup(
    name='rebach',
    version=open("version.py").readlines()[-1].split()[-1].strip("'"),
    packages=['bagger', 'figshare'],
    url='https://github.com/UAL-RE/ReBACH',
    license='MIT License',
    author='University of Arizona Libraries',
    author_email='redata@arizona.edu',
    description='Python-based tool to enable data preservation to a cloud-hosted storage solution ',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=requirements
)

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fr:
    requirements = fr.read().splitlines()

setup(
    name='rebach_bagger',
    version='1.0.0',
    packages=['bagger'],
    url='https://github.com/UAL-RE/ReBACH',
    license='MIT License',
    author='Jonathan Ratliff',
    author_email='jratliff@arizona.edu',
    description='Python-based tool to enable data preservation to a cloud-hosted storage solution ',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=requirements
)

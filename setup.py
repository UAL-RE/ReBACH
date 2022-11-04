from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fr:
    requirements = fr.read().splitlines()

setup(
    name='redata-preservation',
    version='1.0.0',
    packages=['redata-preservation'],
    url='',
    license='MIT License',
    author='Jonathan Ratliff',
    author_email='jratliff@arizona.edu',
    description='Python tool to enable data preservation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=requirements
)

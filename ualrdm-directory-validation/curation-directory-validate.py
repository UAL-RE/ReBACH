# -*- coding: utf-8 -*-
"""
Created on Wed Dec 22 11:28:16 2021

@author: riosf

Validates a given validate_path against the given schema. Uses https://pypi.org/project/directory-schema/
requires jsonschema >=4.0.0
Most of the code is taken and modified from the directory_schema library https://github.com/hubmapconsortium-graveyard/directory-schema

usage: python curation-directory-validate.py [-h] [--test] DIRECTORY SCHEMA

positional arguments:
  DIRECTORY   Directory to validate
  SCHEMA      Schema (JSON or YAML) to validate against

optional arguments:
  -h, --help  show this help message and exit
  --test      run with the hardcoded test values
"""
import os,argparse,sys

from jsonschema.exceptions import SchemaError
from jsonschema import Draft201909Validator,Draft7Validator
from yaml import safe_load as load_yaml
from yaml import dump as dump_yaml

def dir_path(string):
    string=os.path.abspath(string)
    if os.path.isdir(string):
        return string
    else:
        raise Exception(f'"{string}" is not a directory')

def main():
    if len(sys.argv) >= 2 and sys.argv[1]=='--test':
        schema="ual-rdm-directory-schema.json"
        validate_path=os.path.abspath("tests/pass-Fangyue_Zhang_16823602")
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('dir', metavar='DIRECTORY', type=dir_path,
                            help='Directory to validate')
        parser.add_argument('schema', metavar='SCHEMA',
                            help='Schema (JSON or YAML) to validate against')
        parser.add_argument('--test', action='store_true',help='run with the hardcoded test values')                        
        args = parser.parse_args()
    
        schema=args.schema
        validate_path=os.path.abspath(args.dir)
    
        print("Validating: '{0}'".format(validate_path))
    
    #print the JSON-ified directory structure
    print(_dir_to_list(validate_path))

    try:
        print("Using schema {0}".format(schema))
        f=open(schema,"r")
        data=f.read()
        f.close()
        schema_dict = load_yaml(data)
    except Exception as e:
        print("Could not load schema file: {0}".format(e))
        return(1)
    except SchemaError:
        print("Provided document is not valid JSON or YAML Schema")
        return(2)
    
    print()
    print("Validation Results")
    print("------------------")
    try:
        _validate_dir(validate_path, schema_dict)
        print("Success")
    except Exception as e:
        print("Error: {0}".format(e))
          
    return(0)
    
def _dir_to_list(path):
    '''
    Walk the directory at `path`, and return a dict like that from `tree -J`:
    [
      {
        "type": "directory",
        "name": "some-directory",
        "contents": [
          { "type": "file", "name": "some-file.txt" }
        ]
      }
    ]
    '''
    items_to_return = []
    with os.scandir(path) as scan:
        for entry in sorted(scan, key=lambda entry: entry.name):
            is_dir = entry.is_dir()
            item = {
                'type': 'directory' if is_dir else 'file',
                'name': entry.name
            }
            if is_dir:
                item['contents'] = _dir_to_list(os.path.join(path, entry.name))
            items_to_return.append(item)
    return items_to_return

def _validate_dir(path, schema_dict):
    '''
    Given a directory path, and a JSON schema as a dict,
    validate the directory structure against the schema.
    '''
    #the Draft201909Validator check_schema gives a Python recursion error. Use Draft7Validator.
    Draft7Validator.check_schema(schema_dict) 
    
    validator = Draft201909Validator(schema_dict)
    as_list = _dir_to_list(path)
    errors = list(validator.iter_errors(as_list))

    if errors:
        raise DirectoryValidationErrors(errors)        
        
        
def _to_dir_listing(dir_as_list, indent=''):
    next_indent = indent + '    '
    return ''.join([
        '\n' + indent + item['name']
        + _to_dir_listing(
            item['contents'] if 'contents' in item else [],
            next_indent
        )
        for item in dir_as_list
    ])
    
def _validation_error_to_string(error, indent):
    schema_string = ''.join([
        f'\n{indent}{line}' for line in
        dump_yaml(error.schema[error.validator]).split('\n')
    ])
    fail_message = f'''
fails this "{error.validator}" check:
{schema_string}
    '''

    error_type = type(error.instance)

    if error_type == str:
        return f'''This string:
{indent}{error.instance}{fail_message}
        '''

    if error_type == dict:
        return f'''This item:
{_to_dir_listing([error.instance], indent)}{fail_message}
        '''

    if error_type == list:
        return f'''This directory:
{_to_dir_listing(error.instance, indent)}{fail_message}
        '''

    raise Exception(f'Unrecognized type "{error_type}"')
    
class DirectoryValidationErrors(Exception):
    def __init__(self, errors):
        self.json_validation_errors = errors

    def __str__(self):
        return '\n'.join([
            _validation_error_to_string(e, '    ')
            for e in self.json_validation_errors
        ])

    def _repr__(self):
        return self.json_validation_error.__repr__()
    
if __name__ == "__main__":
    sys.exit(main())
# Class for implementing main interactions with dart-runner

import json
import sys
from subprocess import Popen, PIPE


class Job:

    def __init__(self, workflow, bag_name, output_dir, delete,
                 dart_command):
        self.workflow = workflow
        self.bag_name = bag_name
        self.output_dir = output_dir
        self.delete = delete
        self.dart_command = dart_command
        self.files = []
        self.tags = []

    def add_file(self, path):
        self.files.append(path)

    def add_tag(self, tag_file, tag_name, value):
        self.tags.append({
            "tagFile": tag_file,
            "tagName": tag_name,
            "value": value
        })

    def to_json(self):
        _dict = {
            "packageName": self.bag_name,
            "files": self.files,
            "tags": self.tags
        }
        return json.dumps(_dict)

    def run(self):
        json_string = self.to_json()
        cmd = (
            f"{self.dart_command} "
            f"--workflow={self.workflow} "
            f"--output-dir={self.output_dir} "
            f"--delete={self.delete}"
        )
        child = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, close_fds=True,
                      text=True)
        stdout_data, stderr_data = child.communicate(json_string + "\n")
        if stderr_data is not None:
            sys.stderr.write(stderr_data)
        return stdout_data, stderr_data, child.returncode

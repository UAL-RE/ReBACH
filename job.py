import json
import sys
from subprocess import Popen, PIPE

class Job:

#     Replace with .env value
#     Also replace Wasabi credentials with .env value
    dart_command = '/home/jnr/redata/dart-runner'

    def __init__(self, workflow, package_name, output_dir, delete):
        self.workflow = workflow
        self.package_name = package_name
        self.output_dir = output_dir
        self.delete = delete
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
            "packageName": self.package_name,
            "files": self.files,
            "tags": self.tags
        }
        return json.dumps(_dict)

    def run(self) -> int:
        json_string = self.to_json()
        print(json_string)
        print("Starting job")
        cmd = "%s --workflow=%s --output-dir=%s --delete=%s" % (Job.dart_command, self.workflow, self.output_dir, self.delete)
        child = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, close_fds=True, text=True)
        stdout_data, stderr_data = child.communicate(json_string + "\n")
        if stdout_data is not None:
            print(stdout_data)
        if stderr_data is not None:
            sys.stderr.write(stderr_data)
        return child.returncode
import json
from os import PathLike
from subprocess import Popen, PIPE


class Job:

    def __init__(self, workflow: PathLike, bag_name: str, output_dir: PathLike,
                 delete: bool, dart_command: str) -> None:
        """
        Init the Job class with attributes for passing to DART

        :param workflow: Workflow JSON file
        :param bag_name: Name of bag to generate
        :param output_dir: Directory for outputting temp bag prior to upload
        :param delete: Delete the output bag if true
        :param dart_command: Command to run DART executable
        """
        self.workflow: PathLike = workflow
        self.bag_name: str = bag_name
        self.output_dir: PathLike = output_dir
        self.delete: bool = delete
        self.dart_command: str = dart_command
        self.files: list[PathLike] = []
        self.tags: list[dict[str, str]] = []

    def add_file(self, path: PathLike) -> None:
        """
        Add a file to the bag

        :param path: Path to file/directory for package to process
        """
        self.files.append(path)

    def add_tag(self, tag_file: str, tag_name: str, value: str) -> None:
        """
        Add a metadata tag to the bag

        :param tag_file: Name of tag file to which the tag will be added
        :param tag_name: Name of the tag
        :param value: Value of the tag
        """
        self.tags.append(
            {"tagFile": tag_file, "tagName": tag_name, "value": value})

    def to_json(self) -> str:
        """
        Generate JSON string with data for generating bag

        :return: JSON string of bag data to be submitted to DART executable
        """
        _dict = {"packageName": self.bag_name, "files": self.files,
                 "tags": self.tags}
        return json.dumps(_dict)

    def run(self) -> tuple[str, str, int]:
        """
        Run the DART executable with the data provided to the Job class

        :return: Tuple of stdout, stderr, and return code from DART executable
        """
        json_string = self.to_json()
        cmd = (f"{self.dart_command} "
               f"--workflow={self.workflow} "
               f"--output-dir={self.output_dir} "
               f"--delete={self.delete}")
        child = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
                      close_fds=True, text=True)
        stdout_data, stderr_data = child.communicate(json_string + "\n")

        return stdout_data, stderr_data, child.returncode

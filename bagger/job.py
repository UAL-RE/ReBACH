import json
from logging import Logger
from os import PathLike
from subprocess import Popen, PIPE

from bagger import Dryable


class Job:

    def __init__(self, workflow: PathLike, bag_name: str, output_dir: PathLike,
                 delete: bool, dart_command: str, log: Logger) -> None:
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
        self.files: list[str] = []
        self.tags: list[dict[str, str]] = []
        self.log: Logger = log

    def __str__(self):
        return f"Job( workflow='{self.workflow}', bag_name='{self.bag_name}', " \
               f"output_dir='{self.output_dir}', delete={self.delete}, " \
               f"dart_command='{self.dart_command}', log='{self.log.handlers[-1].baseFilename}' " \
               f"files={self.files} " \
               f"tags={self.tags} )" \
               f"\n\nJob Params: {self.to_json()}"

    def add_file(self, path: PathLike) -> None:
        """
        Add a file to the bag

        :param path: Path to file/directory for package to process
        """

        # PathLike is not JSON serializable, so stringify before appending it to files array
        self.files.append(str(path))

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

    @Dryable(('', '', 7))
    def run(self) -> tuple[str, str, int]:
        """
        Run the DART executable with the data provided to the Job class

        :return: Tuple of stdout, stderr, and return code from DART executable
        """
        job_params = self.to_json()

        self.log.debug(f'Job params: {job_params}')

        cmd = (f"{self.dart_command} "
               f"--workflow={self.workflow} "
               f"--output-dir={self.output_dir} "
               f"--delete={self.delete}")
        child = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
                      close_fds=True, text=True)
        stdout_data, stderr_data = child.communicate(job_params + "\n")

        return stdout_data, stderr_data, child.returncode

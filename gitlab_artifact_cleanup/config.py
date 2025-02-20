import os
from configparser import ConfigParser
from enum import Enum, auto
from typing import Any, Optional, TextIO, Union, cast

CONFIG_FILEPATH = "~/.gitlab-artifact-cleanuprc"


class UnknownAlwaysKeepError(Exception):
    pass


class UnknownVerbosityLevelError(Exception):
    pass


class Verbosity(Enum):
    QUIET = auto()
    ERROR = auto()
    WARN = auto()
    VERBOSE = auto()
    DEBUG = auto()


VERBOSITY_CHOICES = tuple(verbosity.name.lower() for verbosity in Verbosity)


class KeepArtifacts(Enum):
    NONE = auto()
    BRANCH_ARTIFACTS = auto()
    TAG_ARTIFACTS = auto()
    BRANCH_AND_TAG_ARTIFACTS = auto()


KEEP_ARTIFACTS_CHOICES = tuple(keep.name.lower() for keep in KeepArtifacts)


class Config:
    _default_config: dict[str, dict[str, Any]] = {
        "general": {
            "verbosity": "verbose",
        },
        "gitlab": {
            "url": "https://gitlab.com/",
            "access_token": f"{' REPLACE OR DELETE ME! ':x^40}",
        },
        "cleanup": {
            "repository_paths": "",
            "always_keep": "branch_and_tag_artifacts",
            "days_to_keep": 7,
            "delete_logs": False,
        },
    }

    @classmethod
    def write_default_config(cls, config_filepath_or_file: Union[str, TextIO] = CONFIG_FILEPATH) -> None:
        default_config = ConfigParser(allow_no_value=True)
        default_config.read_dict(cls._default_config)
        if isinstance(config_filepath_or_file, str):
            config_directory_path = os.path.dirname(os.path.expanduser(config_filepath_or_file))
            if not os.path.exists(config_directory_path):
                os.makedirs(config_directory_path)
            config_file: TextIO
            with open(
                os.path.expanduser(config_filepath_or_file),
                "w",
                encoding="utf-8",
                opener=lambda path, flags: os.open(path, flags, 0o600),
            ) as config_file:
                default_config.write(config_file)
        else:
            config_file = config_filepath_or_file
            default_config.write(config_file)

    def __init__(
        self,
        config_filepath: Optional[str] = CONFIG_FILEPATH,
    ) -> None:
        self._config_filepath = os.path.expanduser(config_filepath) if config_filepath is not None else None
        self._config = ConfigParser(allow_no_value=True)
        self._config.read_dict(self._default_config)
        self.read_config()

    def read_config(self, config_filepath: Optional[str] = None) -> None:
        if config_filepath is not None:
            self._config_filepath = config_filepath
        if self._config_filepath is not None:
            self._config.read(self._config_filepath)

    @property
    def config_filepath(self) -> str:
        assert self._config_filepath is not None
        return self._config_filepath

    @property
    def always_keep(self) -> KeepArtifacts:
        keep_string = self._config["cleanup"].get(
            "always_keep", fallback=self._default_config["cleanup"]["always_keep"]
        )
        if keep_string not in KEEP_ARTIFACTS_CHOICES:
            raise UnknownAlwaysKeepError(
                f'The value {keep_string} is unknow. Valid choices are "{'", "'.join(VERBOSITY_CHOICES)}".'
            )
        return KeepArtifacts[keep_string.upper()]

    @property
    def days_to_keep(self) -> int:
        return self._config["cleanup"].getint("days_to_keep", fallback=self._default_config["cleanup"]["days_to_keep"])

    @property
    def delete_logs(self) -> bool:
        return self._config["cleanup"].getboolean(
            "delete_logs", fallback=self._default_config["cleanup"]["delete_logs"]
        )

    @property
    def gitlab_url(self) -> str:
        return cast(str, self._config["gitlab"].get("url", fallback=str(self._default_config["gitlab"]["url"])))

    @property
    def gitlab_access_token(self) -> Optional[str]:
        access_token = self._config["gitlab"].get("access_token")
        if not access_token or access_token == self._default_config["gitlab"]["access_token"]:
            return None
        return access_token

    @property
    def repository_paths(self) -> Optional[list[str]]:
        repository_paths_string = self._config["cleanup"].get(
            "repository_paths", fallback=self._default_config["cleanup"]["repository_paths"]
        )
        repository_paths = repository_paths_string.split() if repository_paths_string else None
        return repository_paths

    @property
    def verbosity(self) -> Verbosity:
        verbosity_string = self._config["general"].get(
            "verbosity", fallback=self._default_config["general"]["verbosity"]
        )
        if verbosity_string not in VERBOSITY_CHOICES:
            raise UnknownVerbosityLevelError(
                f'The verbosity level "{verbosity_string}" is unknown.'
                f' You can choose from "{'", "'.join(VERBOSITY_CHOICES)}".'
            )
        return Verbosity[verbosity_string.upper()]


config = Config()

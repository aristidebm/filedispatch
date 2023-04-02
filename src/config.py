import logging
import yaml
from typing import List, Union
from pathlib import Path
from pydantic import BaseModel, BaseSettings, DirectoryPath, constr, HttpUrl
from pydantic_yaml import YamlModelMixin
from pydantic.error_wrappers import ValidationError

from .utils import FtpUrl

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FolderModel(BaseModel):
    path: Union[str, HttpUrl, FtpUrl, Path]
    # https://en.wikipedia.org/wiki/List_of_filename_extensions
    extensions: List[constr(max_length=10)]


class Settings(YamlModelMixin, BaseSettings):
    source: DirectoryPath
    folders: List[FolderModel]


class Config:
    def __init__(self, config: Union[str, Path]):
        self.config = config

    def __call__(self, *args, **kwargs):
        try:
            logger.info("Parsing config file ...")
            config = Settings.parse_file(self.config)
            self._log_config()
            return config
        except (ValidationError, ValueError, OSError) as exp:
            logger.error(exp)
            logger.debug(exp)
            return

    def _log_config(self):
        with open(self.config) as f:
            logger.info(f"\n{f.read()}\n")


def parse_logger_config(path):
    config = None
    try:
        with open(path, "r") as stream:
            config = yaml.safe_load(stream)
    except OSError:
        pass
    return config

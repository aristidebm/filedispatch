import logging
from typing import List, Union
from pathlib import Path
from pydantic import BaseModel, BaseSettings, DirectoryPath, constr
from pydantic_yaml import YamlModelMixin, yaml
from pydantic.error_wrappers import ValidationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FolderModel(BaseModel):
    label: constr(max_length=255)
    path: DirectoryPath
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
            return Settings.parse_file(self.config)
        except (ValidationError, ValueError, OSError) as exp:
            logger.error(exp)
            logger.debug(exp)
            return

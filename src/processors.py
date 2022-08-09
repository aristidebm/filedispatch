from typing import Union
from pathlib import Path
import abc
import os
import shutil
import logging

PATH = Union[str, Path]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseProcessor(abc.ABC):
    ...

    @abc.abstractmethod
    def process(self, filename, destination, **kwargs) -> None:
        ...


class LocalStorageProcessor(BaseProcessor):
    ...

    def process(self, filename: PATH, destination: PATH, **kwargs):
        return self._move(filename, destination)

    def _move(self, filename: PATH, dest: PATH):
        try:
            # See hereh wy we choose it over os.rename os.rename
            # https://www.codespeedy.com/difference-between-os-rename-and-shutil-move-in-python/
            basename = os.path.basename(filename)
            shutil.move(filename, os.path.join(dest, basename))
        except OSError as exp:
            logger.exception(exp)

        logger.info(f"File {filename} moved to {dest}")


class RemoteStorageProcessor(BaseProcessor):
    ...

    def process(self, filename, destination, **kwargs):
        ...


class FtpStorageProcessor(RemoteStorageProcessor):
    ...

    def process(self, filename, destination, **kwargs):
        ...


class HttpStorageProcessor(RemoteStorageProcessor):
    ...

    def process(self, filename, destination, **kwargs):
        ...

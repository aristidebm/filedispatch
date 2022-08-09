from typing import Union
from pathlib import Path
from asyncio import Queue
import abc
import os
import shutil
import logging

PATH = Union[str, Path]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def produce(f):
    def wrapper(self, filename, destination, *args, **kwargs):
        await self.unprocessed.put((filename, destination))

    return wrapper


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
    def __init__(self):
        self.unprocessed = Queue()
        # FIXME: can't do async stuff in __init__. can't decorate coroutine like that.
        self.process = produce(self.process)(self)

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

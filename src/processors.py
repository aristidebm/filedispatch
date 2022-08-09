from typing import Union
from pathlib import Path
from functools import wraps
from asyncio import Queue
import abc
import os
import shutil
import logging

from aiofiles.os import wrap

PATH = Union[str, Path]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RemoteStorageMixin:
    # FIXME: Make the function more generic.
    @classmethod
    def produce(cls, method):
        f = getattr(cls, method, None)

        if not callable(f):
            return

        @wraps(f)
        async def wrapper(self, filename, destination, **kwargs):
            await self.unprocessed.put((filename, destination))
            await f(self, filename, destination, **kwargs)
            await self.unprocessed.task_done()

        setattr(cls, wrapper.__name__, wrapper)


class BaseStorageProcessor(abc.ABC):
    fancy_name = "Base Processor"

    @abc.abstractmethod
    async def process(self, filename, destination, **kwargs) -> None:
        ...

    @classmethod
    def create(cls, **kwargs):
        instance = cls()
        return instance


class RemoteStorageProcessor(RemoteStorageMixin, BaseStorageProcessor):

    fancy_name = "Remote Processor"

    @classmethod
    def create(cls, **kwargs):
        instance = super().create()
        instance.unprocessed = Queue()
        cls.produce("process")
        return instance


class LocalStorageProcessor(BaseStorageProcessor):

    fancy_name = "Local processor"

    async def process(self, filename: PATH, destination: PATH, **kwargs):
        return self._move(filename, destination)

    # replace this with async version using this thread https://stackoverflow.com/a/70586756/13837279.
    async def _move(self, filename: PATH, dest: PATH):
        move = wrap(shutil.move)
        try:
            # See hereh wy we choose it over os.rename os.rename
            # https://www.codespeedy.com/difference-between-os-rename-and-shutil-move-in-python/
            basename = os.path.basename(filename)
            # await move(filename, os.path.join(dest, basename))
            await move(filename, os.path.join(dest, basename))
        except OSError as exp:
            logger.exception(exp)

        logger.info(f"File {filename} moved to {dest}")


class FtpStorageProcessor(RemoteStorageProcessor):

    fancy_name = "FTP processor"

    async def process(self, filename, destination, **kwargs) -> None:
        ...


class HttpStorageProcessor(RemoteStorageProcessor):

    fancy_name = "HTTP processor"

    async def process(self, filename, destination, **kwargs) -> None:
        ...

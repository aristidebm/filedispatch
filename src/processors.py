from typing import Tuple
from functools import wraps, cached_property
from asyncio import Queue
import abc
import os
import shutil
import logging

import mode
from aiofiles.os import wrap
import aiohttp
import aioftp

from api.models import LogEntry, ProtocolEnum, StatusEnum
from .utils import PATH, get_protocol
from .notifiers import Notifier


@cached_property
def notifier(self):
    return Notifier()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
async_move = wrap(shutil.move)


# class RemoteStorageMixin:
#     # FIXME: Make the function more generic.
#     @classmethod
#     def produce(cls, method):
#         f = getattr(cls, method, None)
#
#         if not callable(f):
#             return
#
#         @wraps(f)
#         async def wrapper(self, filename: PATH, destination: PATH, **kwargs):
#             await self.unprocessed.put((filename, destination))
#             await f(self, filename, destination, **kwargs)
#             await self.unprocessed.task_done()
#
#         setattr(cls, wrapper.__name__, wrapper)


class BaseStorageProcessor(abc.ABC, mode.Service):

    fancy_name: str = "Base Processor"
    notifier: Notifier = None

    def __init__(self):
        super().__init__()
        self.unprocessed: Queue[Tuple[PATH, PATH]] = Queue()

    async def on_start(self) -> None:
        await self.add_runtime_dependency(self.notifier)

    async def _notify(self, filename, destination, status, reason=None, **kwargs):
        payload = self._get_payload(filename, destination, status, reason)
        await self.notifier.acquire(payload)

    def _get_payload(self, filename, destination, status, reason=None):
        def get_filesize():

            stat_object = os.stat(filename)
            suffix = ["KB", "MB", "GB", "TB"]
            quot = stat_object.st_size
            size = None
            idx = -1

            while quot:
                size, quot = quot, quot // 1024
                idx += 1
                # stop on terabytes
                if idx == len(suffix) - 1:
                    break

            if size:
                size = f"{size} {suffix[idx]}"
            else:
                size = f"{stat_object.st_size // 1024} {suffix[0]}"

            return size

        basename = os.path.basename(filename)
        extension = os.path.splitext(basename)[1]

        return LogEntry(
            filename=basename,
            destination=destination,
            extension=extension,
            processor=self.fancy_name,
            protocol=ProtocolEnum[get_protocol(destination)],
            status=status,
            size=get_filesize(),
            reason=reason,
        ).dict()

    @cached_property
    def notifier(self):
        return Notifier()

    @abc.abstractmethod
    async def _process(self, **kwargs):
        pass

    async def acquire(self, filename: PATH, destination: PATH, **kwargs) -> None:
        await self.unprocessed.put((filename, destination))


class LocalStorageProcessor(BaseStorageProcessor):

    fancy_name = "Local processor"

    @mode.Service.task
    async def _process(self, filename: PATH, destination: PATH, **kwargs):
        await self._move()

    async def _move(self):
        filename, destination = await self.unprocessed.get()
        try:
            basename = os.path.basename(filename)
            await async_move(filename, os.path.join(destination, basename))
            logger.info(f"File {filename} moved to {destination}")
            await self._notify(filename, destination, StatusEnum.SUCCEEDED)

        except OSError as exp:
            logger.exception(exp)
            await self._notify(
                filename, destination, StatusEnum.FAILED, reason=" ".join(exp.args)
            )


class FtpStorageProcessor(BaseStorageProcessor):

    fancy_name = "FTP processor"

    @mode.Service.task
    async def _process(self, **kwargs):
        pass


class HttpStorageProcessor(BaseStorageProcessor):

    fancy_name = "HTTP processor"

    @mode.Service.task
    async def _process(self, **kwargs):
        pass

    async def _send(self, filename, destination, **kwargs):
        # https://docs.aiohttp.org/en/stable/
        # https://docs.aiohttp.org/en/stable/multipart.html#sending-multipart-requests
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types#multipartform-data
        async with aiohttp.ClientSession() as session:
            async with session.post(destination) as response:
                print("Status:", response.status)
                print("Content-type:", response.headers["content-type"])

                html = await response.text()
                print("Body:", html[:15], "...")

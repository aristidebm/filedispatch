import math
from typing import Tuple, Optional
from functools import wraps, cached_property
from asyncio import Queue
import abc
import os
import shutil
import logging

from pydantic import parse_obj_as, error_wrappers

import mode
import aiohttp
import aioftp
import aiofiles
from aiofiles.os import wrap
from aiohttp_retry import RetryClient, ExponentialRetry
from aiohttp.client_exceptions import ClientError

from src.api.models import LogEntry, ProtocolEnum, StatusEnum
from .utils import PATH, get_protocol, FtpUrl
from .notifiers import Notifier

copyfile = wrap(shutil.copyfile)


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

# Resources
# https://phil.tech/2016/http-rest-api-file-uploads/
# https://developer.mozilla.org/en-US/docs/Learn/Common_questions/Upload_files_to_a_web_server


class BaseStorageProcessor(mode.Service):

    fancy_name: str = "Base Processor"
    notifier: Notifier = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unprocessed: Queue[Tuple[PATH, PATH]] = Queue()

    async def on_start(self) -> None:
        await self.add_runtime_dependency(self.notifier)

    async def _notify(
        self, filename, destination, status, reason=None, delete=False, **kwargs
    ):
        try:
            payload = await self._get_payload(filename, destination, status, reason)
        except (error_wrappers.ValidationError, OSError) as exp:
            self.logger.debug(exp)
        else:
            await self.notifier.acquire(payload)
            if delete:
                try:
                    await aiofiles.os.unlink(filename)
                except OSError as exp:
                    self.logger.debug(exp)

    async def _get_payload(self, filename, destination, status, reason=None):
        async def get_filesize():
            suffix = ["KB", "MB", "GB", "TB"]
            quot = st_size = await aiofiles.os.path.getsize(filename)
            size = None
            idx = -1

            while math.floor(quot):
                size, quot = quot, quot / 1024
                idx += 1
                # stop on terabytes
                if idx == len(suffix) - 1:
                    break

            if size:
                size = f"{size: .2f} {suffix[idx]}"
            else:
                size = f"{st_size / 1024: .2f} {suffix[0]}"

            return size

        extension = os.path.splitext(filename)[1].removeprefix(".")

        return LogEntry(
            filename=os.path.basename(filename),
            destination=str(destination),
            source=os.path.dirname(filename),
            extension=extension,
            processor=self.fancy_name.upper(),
            protocol=ProtocolEnum[get_protocol(destination)],
            status=status,
            size=await get_filesize(),
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
    async def _process(self, **kwargs):
        await self._move()

    async def _move(self, **kwargs):
        filename, destination = await self.unprocessed.get()
        try:
            basename = os.path.basename(filename)
            await copyfile(filename, os.path.join(destination, basename))
            self.logger.info(f"File {filename} moved to {destination}")
            await self._notify(filename, destination, StatusEnum.SUCCEEDED, delete=True)

        except OSError as exp:
            self.logger.exception(exp)
            reason = " ".join(exp.args)
            await self._notify(filename, destination, StatusEnum.FAILED, reason)


class HttpStorageProcessor(BaseStorageProcessor):

    fancy_name = "HTTP processor"

    @mode.Service.task
    async def _process(self, **kwargs):
        await self._send(**kwargs)

    async def _send(self, **kwargs):
        # https://docs.aiohttp.org/en/stable/multipart.html#sending-multipart-requests

        filename, destination = await self.unprocessed.get()

        with aiohttp.MultipartWriter() as writer:
            try:
                # FIXME: The content getter must depend on the file size,
                #  we  must use _send_chunk for big files (State the definition of big)
                writer.append(await aiofiles.open(filename, "rb"))
            except OSError as exp:
                self.logger.exception(exp)
                reason = " ".join(exp.args)
                await self._notify(filename, destination, StatusEnum.FAILED, reason)
                return

            async with RetryClient() as client:
                try:
                    async with client.post(destination, data=writer) as response:
                        if response.ok:
                            await self._notify(
                                filename, destination, StatusEnum.SUCCEEDED
                            )
                        else:
                            reason = await response.text()
                            reason = f"{response.status} {response.reason}\n\n{reason}"
                            self.logger.debug(reason)
                            await self._notify(
                                filename, destination, StatusEnum.FAILED, reason
                            )
                except ClientError as exp:
                    self.logger.debug(exp)
                    reason = " ".join(exp.args)
                    await self._notify(filename, destination, StatusEnum.FAILED, reason)

    # https://docs.aiohttp.org/en/stable/client_quickstart.html#streaming-uploads
    async def _send_chunk(self, filename):  # useful for big files
        async with aiofiles.open(filename, "rb") as f:
            chunk = await f.read(64 * 1024)
            while chunk:
                yield chunk
                chunk = await f.read(64 * 1024)


class FtpStorageProcessor(BaseStorageProcessor):

    fancy_name = "FTP processor"

    @mode.Service.task
    async def _process(self, **kwargs):
        await self._send(**kwargs)

    async def _send(self, **kwargs):
        filename, destination = await self.unprocessed.get()

        try:
            scheme = parse_obj_as(FtpUrl, destination)
        except error_wrappers.ValidationError as exp:
            self.logger.exception(exp)
            reason = exp.json()
            await self._notify(filename, destination, StatusEnum.FAILED, reason)
            return
        else:
            if not all([scheme.host, scheme.port, scheme.user, scheme.password]):
                reason = f"Missing connection information (host, port, username, password) in {destination}"
                await self._notify(filename, destination, StatusEnum.FAILED, reason)
                return

        async with aioftp.Client.context(
            scheme.host, port=scheme.path, user=scheme.user, password=scheme.password
        ) as client:
            try:
                await client.upload(filename)
            except aioftp.StatusCodeError as exp:
                reason = f"Received {exp.received_codes}\n\nExpected{exp.expected_codes}\n\n{exp.info}"
                await self._notify(filename, destination, StatusEnum.FAILED, reason)

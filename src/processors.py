import asyncio
import functools
import math
from typing import Tuple, Optional
from functools import wraps, cached_property
from asyncio import Queue
import abc
import os
import shutil

from pydantic import parse_obj_as, error_wrappers

import mode
import aiohttp
import aioftp
import aiofiles
import aiofiles.os as aiofiles_os
from aiohttp_retry import RetryClient

from .utils import (
    PATH,
    get_payload,
    FtpUrl,
    StatusEnum,
)

copyfile = aiofiles_os.wrap(shutil.copyfile)
unlink = aiofiles_os.wrap(os.unlink)


class BaseStorageProcessor(mode.Service):
    abstract = True

    fancy_name: str = "Base Processor"

    def __init__(self, notifier=None, with_web_app=True, **kwargs):
        self._with_web_app = with_web_app
        self._notifier = notifier
        super().__init__(**kwargs)

    async def on_start(self) -> None:
        await super().on_start()
        # define before background task start since the use Queues
        # for the matter of safety https://mode.readthedocs.io/en/latest/userguide/services.html#ordering
        self.unprocessed: Queue[Tuple[PATH, PATH]] = Queue()
        if self.with_web_app:
            self.add_dependency(self.notifier)

    async def _notify(
        self, filename, destination, status, reason=None, delete=False, **kwargs
    ):
        if not self.with_web_app:
            return
        try:
            payload = await get_payload(
                filename, destination, status, self.fancy_name, reason
            )
        except error_wrappers.ValidationError as exp:
            self.logger.debug(exp)
        else:
            # Start notifier on demand (because notifier isn't added using running add_runtime_dependencies)
            await self.notifier.maybe_start()
            self.notifier.acquire(payload)
            if delete and status != StatusEnum.FAILED:
                try:
                    await unlink(filename)
                except OSError as exp:
                    self.logger.debug(exp)

    @property
    def notifier(self):
        return self._notifier

    @notifier.setter
    def notifier(self, notifier):
        self._notifier = notifier

    @property
    def with_web_app(self):
        return self._with_web_app

    @with_web_app.setter
    def with_web_app(self, value):
        self._with_web_app = value

    @abc.abstractmethod
    async def process(self, filename, destination, delete=False, **kwargs):
        pass

    @mode.Service.task
    async def _consume(self, **kwargs):
        while not self.should_stop:
            filename, destination = await self.unprocessed.get()
            asyncio.create_task(self.process(filename, destination, **kwargs))
            await self.sleep(1.0)

    def acquire(self, filename: PATH, destination: PATH, **kwargs) -> None:
        asyncio.create_task(self.unprocessed.put((filename, destination)))


class LocalStorageProcessor(BaseStorageProcessor):
    fancy_name = "Local processor"

    async def process(self, filename, destination, delete=False, **kwargs):

        try:
            basename = os.path.basename(filename)
            await copyfile(filename, os.path.join(destination, basename))
            self.logger.info(f"File {filename} moved to {destination}")
            asyncio.create_task(
                self._notify(filename, destination, StatusEnum.SUCCEEDED, delete=delete)
            )
        except OSError as exp:
            self.logger.exception(exp)
            reason = " ".join([str(arg) for arg in exp.args])
            asyncio.create_task(
                self._notify(filename, destination, StatusEnum.FAILED, reason)
            )


class HttpStorageProcessor(BaseStorageProcessor):
    fancy_name = "HTTP processor"

    async def process(self, filename, destination, delete=False, **kwargs):
        # https://docs.aiohttp.org/en/stable/multipart.html#sending-multipart-requests

        with aiohttp.MultipartWriter() as writer:
            try:
                # FIXME: The content getter must depend on the file size,
                #  we  must use _send_chunk for big files (State the definition of big)
                writer.append(await aiofiles.open(filename, "rb"))
            except OSError as exp:
                self.logger.exception(exp)
                reason = " ".join([str(arg) for arg in exp.args])
                await self._notify(filename, destination, StatusEnum.FAILED, reason)
                return

            async with RetryClient() as client:
                async with client.post(destination, data=writer) as response:
                    if response.ok:
                        await self._notify(filename, destination, StatusEnum.SUCCEEDED)
                    else:
                        reason = await response.text()
                        reason = f"{response.status} {response.reason}\n\n{reason}"
                        self.logger.debug(reason)
                        await self._notify(
                            filename, destination, StatusEnum.FAILED, reason
                        )

    # https://docs.aiohttp.org/en/stable/client_quickstart.html#streaming-uploads
    async def _send_chunk(self, filename):  # useful for big files
        async with aiofiles.open(filename, "rb") as f:
            chunk = await f.read(64 * 1024)
            while chunk:
                yield chunk
                chunk = await f.read(64 * 1024)


class FtpStorageProcessor(BaseStorageProcessor):
    fancy_name = "FTP processor"

    async def process(self, filename, destination, delete=False, **kwargs):
        # FIXME: move destination validation to the top level class and leave.

        try:
            scheme = parse_obj_as(FtpUrl, destination)
        except error_wrappers.ValidationError as exp:
            self.logger.warning(exp)
            self.logger.debug(exp, stack_info=True)
            reason = f"The destination path « {destination} » is not valid ftp url."
            await self._notify(filename, destination, StatusEnum.FAILED, reason)
            return

        async with aioftp.Client.context(
            scheme.host, port=scheme.path, user=scheme.user, password=scheme.password
        ) as client:
            try:
                await client.upload(filename, destination)
                await self._notify(filename, destination, StatusEnum.SUCCEEDED)
            except aioftp.StatusCodeError as exp:
                self.logger.warning(exp)
                self.logger.debug(exp, stack_info=True)
                reason = f"Received {exp.received_codes}\n\nExpected{exp.expected_codes}\n\n{exp.info}"
                await self._notify(filename, destination, StatusEnum.FAILED, reason)
            except aioftp.AIOFTPException as exp:
                self.logger.warning(exp)
                self.logger.debug(exp, stack_info=True)
                reason = f"{exp}"
                await self._notify(filename, destination, StatusEnum.FAILED, reason)

import asyncio
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

from .utils import PATH, get_payload, FtpUrl, StatusEnum, Message

copyfile = aiofiles_os.wrap(shutil.copyfile)
unlink = aiofiles_os.wrap(os.unlink)


def is_processable(message: Message):
    filename = message.body.get("filename")
    destination = message.body.get("destination")
    return filename and destination


class BaseWorker(mode.Service):
    abstract = True

    fancy_name: str = "Base Processor"

    def __init__(self, notifier=None, **kwargs):
        self._notifier = notifier
        self.unprocessed: Queue[Message] = Queue()
        self._delete = kwargs.get("delete", False)
        super().__init__(**kwargs)

    async def on_start(self) -> None:
        self.add_dependency(self.notifier)
        await super().on_start()

    async def _notify(
        self,
        message,
        status,
        reason=None,
        delete=False,
        **kwargs,
    ):
        if not self.notifier:
            return

        filename = message.body.get("filename")
        destination = message.body.get("destination")

        try:
            payload = await get_payload(
                filename, destination, status, self.fancy_name, reason
            )
        except error_wrappers.ValidationError as exp:
            self.logger.debug(exp)
            return

        await self.notifier.maybe_start()
        self.notifier.acquire(payload)

        if delete and status != StatusEnum.FAILED:
            try:
                filename = message.body.get("filename") or ""
                await unlink(filename)
            except OSError as exp:
                self.logger.debug(exp)

    @property
    def notifier(self):
        return self._notifier

    @notifier.setter
    def notifier(self, notifier):
        self._notifier = notifier

    @abc.abstractmethod
    async def process(self, message: Message, delete=False, **kwargs):
        pass

    async def consume(self, **kwargs):
        message = await self.unprocessed.get()
        asyncio.create_task(self.process(message, delete=self._delete, **kwargs))
        await self.sleep(1.0)

    def acquire(self, message: Message, **kwargs) -> None:
        asyncio.create_task(self.unprocessed.put(message))

    def add_dependency(self, service):
        if not service:
            return
        return super().add_dependency(service)


class FileWorker(BaseWorker):
    fancy_name = "File worker"

    async def process(self, message, delete=False, **kwargs):
        if not is_processable(message):
            return

        filename = message.body.get("filename")
        destination = message.body.get("destination")

        try:
            basename = os.path.basename(filename)
            await copyfile(filename, os.path.join(destination, basename))
            self.logger.info(f"File {filename} moved to {destination}")
            asyncio.create_task(
                self._notify(message, StatusEnum.SUCCEEDED, delete=delete)
            )
        except OSError as exp:
            self.logger.exception(exp)
            reason = " ".join([str(arg) for arg in exp.args])
            asyncio.create_task(self._notify(message, StatusEnum.FAILED, reason))

    @mode.Service.task
    async def _consume(self):
        while not self.should_stop:
            await self.consume()


class HttpWorker(BaseWorker):
    fancy_name = "HTTP worker"

    async def process(self, message, delete=False, **kwargs):
        if not is_processable(message):
            return

        filename = message.body.get("filename")
        destination = message.body.get("destination")

        with aiohttp.MultipartWriter() as writer:
            try:
                # FIXME: The content getter must depend on the file size,
                #  we  must use _send_chunk for big files (State the definition of big)
                writer.append(await aiofiles.open(filename, "rb"))
            except OSError as exp:
                self.logger.exception(exp)
                reason = " ".join([str(arg) for arg in exp.args])
                await self._notify(message, StatusEnum.FAILED, reason)
                return

            async with RetryClient() as client:
                async with client.post(destination, data=writer) as response:
                    if response.ok:
                        await self._notify(message, StatusEnum.SUCCEEDED)
                    else:
                        reason = await response.text()
                        reason = f"{response.status} {response.reason}\n\n{reason}"
                        self.logger.debug(reason)
                        await self._notify(message, StatusEnum.FAILED, reason)

    async def _send_chunk(self, filename):  # useful for big files
        async with aiofiles.open(filename, "rb") as f:
            chunk = await f.read(64 * 1024)
            while chunk:
                yield chunk
                chunk = await f.read(64 * 1024)

    @mode.Service.task
    async def _consume(self):
        while not self.should_stop:
            await self.consume()


class FtpWorker(BaseWorker):
    fancy_name = "FTP worker"

    async def process(self, message, delete=False, **kwargs):
        if not is_processable(message):
            return

        filename = message.body.get("filename")
        destination = message.body.get("destination")

        try:
            scheme = parse_obj_as(FtpUrl, destination)
        except error_wrappers.ValidationError as exp:
            self.logger.warning(exp)
            self.logger.debug(exp, stack_info=True)
            reason = f"The destination path « {destination} » is not valid ftp url."
            await self._notify(filename, destination, StatusEnum.FAILED, reason)
            return

        async with aioftp.Client.context(
            scheme.host, port=scheme.port, user=scheme.user, password=scheme.password
        ) as client:
            try:
                await client.upload(filename, destination)
                await self._notify(message, StatusEnum.SUCCEEDED)
            except aioftp.StatusCodeError as exp:
                self.logger.warning(exp)
                self.logger.debug(exp, stack_info=True)
                reason = f"Received {exp.received_codes}\n\nExpected{exp.expected_codes}\n\n{exp.info}"
                await self._notify(message, StatusEnum.FAILED, reason)
            except aioftp.AIOFTPException as exp:
                self.logger.warning(exp)
                self.logger.debug(exp, stack_info=True)
                reason = f"{exp}"
                await self._notify(message, StatusEnum.FAILED, reason)

    @mode.Service.task
    async def _consume(self):
        while not self.should_stop:
            await self.consume()

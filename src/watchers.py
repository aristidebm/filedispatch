import os
import logging
import functools
from typing import Tuple
from pathlib import Path
from asyncio import Queue

import mode
from watchfiles import awatch, Change
import aiofiles

from src.api.server import WebServer
from .processors import LocalStorageProcessor, FtpStorageProcessor, HttpStorageProcessor
from .utils import get_protocol, PATH
from .config import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseWatcher(mode.Service):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls._register_processor()

    @classmethod
    def _register_processor(cls):
        cls.PROCESSORS_REGISTRY = dict(
            file=LocalStorageProcessor(),
            ftp=FtpStorageProcessor(),
            http=HttpStorageProcessor(),
        )


class FileWatcher(BaseWatcher):

    server: WebServer = None

    def __init__(self, config: Settings, **kwargs):
        self._port = kwargs.pop("port", None)
        super().__init__(**kwargs)
        self.config = config
        self.unprocessed: Queue[Tuple[PATH, PATH]] = Queue()

    async def on_start(self) -> None:
        # The server will be closed automatically when FileWatcher is suspended
        # since the server is a runtime dependency
        await self.add_runtime_dependency(self.server)

    async def on_stop(self) -> None:
        # stop processor
        for processor in self.PROCESSORS_REGISTRY.values():
            logger.info(f"Stopping [{processor.fancy_name.lower()}] ...")
            await processor.stop()
        await super().on_stop()

    def on_init_dependencies(self):
        super().on_init_dependencies()
        # update the loop.
        for process in self.PROCESSORS_REGISTRY.values():
            process.loop = self.loop
        return self.PROCESSORS_REGISTRY.values()

    async def on_started(self) -> None:
        await super().on_started()
        await self._collect_unprocessed(config=self.config)

    async def _collect_unprocessed(self, config=None):
        config = config or self.config
        supported = {e: f.path for f in config.folders for e in f.extensions}
        for ext in supported:
            # glob doesn't support multiple extension globing
            for filename in Path(self.config.source).glob(f"*.{ext}"):
                dest = self._find_destination(filename, config, supported)

                if not dest:
                    continue

                await self.unprocessed.put((filename, dest))
                self.logger.debug(f"File {filename} is appended to be processed")

    @functools.cached_property
    def server(self):
        return WebServer(port=self._port)

    @mode.Service.task
    async def _watch(self, config=None):
        config = config or self.config
        async for changes in awatch(config.source):
            for change in changes:
                # consider only adds, ignore all other changes.
                if Change.added not in change:
                    continue

                filename = change[1]
                # Ignore files added in the source subdirectories since watchfiles do recursive watch
                # An issue is opened to fix that here https://github.com/samuelcolvin/watchfiles/issues/178
                if os.path.basename(os.path.dirname(filename)) != os.path.basename(
                    config.source
                ):
                    continue

                # Ignore directories and symlinks
                if not await aiofiles.os.path.isfile(filename):
                    continue

                dest = self._find_destination(filename, config=config)

                if not dest:
                    continue

                await self.unprocessed.put((filename, dest))
                self.logger.info(f"File {filename} is appended to be processed")

    @mode.Service.task
    async def _provide(self):
        while not self.should_stop:
            await self.sleep(1.0)
            filename, destination = await self.unprocessed.get()
            processor = self._get_processor(destination)
            # start the processor if not yet started.
            await processor.maybe_start()
            await processor.acquire(filename, destination)
            self.unprocessed.task_done()

    def _get_processor(self, destination, **kwargs):
        processor = self.PROCESSORS_REGISTRY[get_protocol(destination)]
        self.logger.info(f"{processor.fancy_name} is used to process {destination}")
        return processor

    def _find_destination(self, filename: PATH, config=None, mapping=None) -> PATH:
        mapping = mapping or {}
        config = config or self.config
        _, ext = os.path.splitext(filename)
        ext = ext.lower().removeprefix(".")

        if path := mapping.get(ext):
            return path

        for folder in config.folders:
            if ext in folder.extensions:
                return folder.path

    def run(self, loglevel="INFO", logfile=None, handlers=None):
        try:
            worker = mode.Worker(
                self,
                loglevel=loglevel,
                logfile=logfile,
                loghandlers=handlers,
                redirect_stdouts=False,
            )
            worker.execute_from_commandline()
        except Exception as exp:
            self.logger.exception(exp)
            return

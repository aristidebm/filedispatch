import asyncio
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
from .notifiers import Notifier
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
    def __init__(
        self,
        config: Settings,
        *,
        host: str = None,
        port: int = None,
        log_file: PATH = None,
        log_level: str = None,
        with_webapp: bool = False,
        **kwargs,
    ):
        self._config = config
        self._web_app_host = host or 3001
        self._web_app_port = port or "127.0.0.1"
        self._with_webapp = with_webapp
        self._log_file = log_file
        self._log_level = log_level
        self.unprocessed: Queue[Tuple[PATH, PATH]] | None = None
        super().__init__(**kwargs)

    def __post_init__(self) -> None:
        self._init_processors()
        if self._with_webapp:
            self.add_dependency(self.server)
            self.logger.info("The web-app is enabled.")
        else:
            self.logger.info("The web-app is disabled.")

    async def on_start(self):
        await super().on_start()
        self.unprocessed = Queue()

    def on_init_dependencies(self):
        dependencies = super().on_init_dependencies()
        dependencies += self.PROCESSORS_REGISTRY.values()
        return dependencies

    def _init_processors(self) -> list[mode.ServiceT]:
        processors = []
        for p in self.PROCESSORS_REGISTRY.values():
            if self._with_webapp:
                # FIXME: Perhaps only one Notify is suffisent ? It can be interesting
                #  to consider if we are sure of less traffic between processors and notifier.
                p.notifier = Notifier(
                    loop=self.loop,
                    host=self._web_app_host,
                    port=self._web_app_port,
                    scheme="http",
                )
            # share the same loop between all dependencies so that we will not experiment wired
            # behavior due to each dependency runs on it own event loop.
            p.loop = self.loop
            processors.append(p)

        return processors

    async def on_started(self) -> None:
        if self._with_webapp:
            await self.server.maybe_start()
        await self._collect_unprocessed(config=self._config)
        await super().on_started()

    async def _collect_unprocessed(self, config=None):
        config = config or self._config
        supported = {e: f.path for f in config.folders for e in f.extensions}
        collected = []
        for ext in supported:
            # glob doesn't support multiple extension globing
            for filename in Path(self._config.source).glob(f"*.{ext}"):
                dest = self._find_destination(filename, config, supported)

                if not dest or filename in collected:
                    continue

                collected.append(filename)
                asyncio.create_task(self.unprocessed.put((filename, dest)))
                self.logger.debug(f"File {filename} is appended to be processed")

    @functools.cached_property
    def server(self):
        return WebServer(
            loop=self.loop,
            host=self._web_app_host,
            port=self._web_app_port,
        )

    @mode.Service.task
    async def _watch(self, config=None):
        config = config or self._config
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

                # we don't need this to be completed before we continue, so we don't need to block uselessly.
                asyncio.create_task(self.unprocessed.put((filename, dest)))
                self.logger.info(f"File {filename} is appended to be processed")

    @mode.Service.task
    async def _provide(self):
        while not self.should_stop:
            filename, destination = await self.unprocessed.get()
            processor = self._get_processor(destination)
            # start the processor if not yet started.
            await processor.maybe_start()
            processor.acquire(filename, destination)
            self.unprocessed.task_done()
            await self.sleep(1.0)

    def _get_processor(self, destination, **kwargs):
        processor = self.PROCESSORS_REGISTRY[get_protocol(destination)]
        self.logger.info(f"{processor.fancy_name} is used to process {destination}")
        return processor

    def _find_destination(self, filename: PATH, config=None, mapping=None) -> PATH:
        mapping = mapping or {}
        config = config or self._config
        _, ext = os.path.splitext(filename)
        ext = ext.lower().removeprefix(".")

        if path := mapping.get(ext):
            return path

        for folder in config.folders:
            if ext in folder.extensions:
                return folder.path

    def run(self):
        log_level = getattr(logging, self._log_level or "", logging.INFO)
        try:
            worker = mode.Worker(
                self,
                debug=bool(log_level == logging.DEBUG),
                daemon=True,
                loglevel=log_level,
                logfile=self._log_file,
                redirect_stdouts=False,
            )
            worker.execute_from_commandline()
        except Exception as exp:
            self.logger.exception(exp)
            return

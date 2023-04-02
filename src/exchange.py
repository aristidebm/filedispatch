import os
import logging
import functools
from pathlib import Path
from asyncio import Queue

import mode
from watchfiles import awatch, Change
import aiofiles

from src.api.server import WebServer
from .workers import FileWorker, FtpWorker, HttpWorker
from .notifiers import Notifier
from .utils import PATH, Message, create_message
from .routers import Router, DefaultRouter
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
            file=FileWorker(),
            ftp=FtpWorker(),
            http=HttpWorker(),
        )


class FileWatcher(BaseWatcher):
    def __init__(
        self,
        config: Settings,
        router: Router | None = None,
        *,
        host: str = None,
        port: int = None,
        log_file: PATH = None,
        log_level: str = None,
        with_webapp: bool = False,
        delete: bool = False,
        db: str = None,
        **kwargs,
    ):
        self._config = config
        self._web_app_host = host or "127.0.0.1"
        self._web_app_port = port or 3001
        self._with_webapp = with_webapp
        self._log_file = log_file
        self._log_level = log_level
        self.unprocessed: Queue[Message] = Queue()
        self._router = router or DefaultRouter(workers=self.PROCESSORS_REGISTRY)
        self._delete = delete
        self._db = db
        super().__init__(**kwargs)

    def __post_init__(self) -> None:
        self._init_workers()
        if self._with_webapp:
            self.add_dependency(self.server)
            self.logger.info("The webapp is enabled.")
        else:
            self.logger.info("The webapp is disabled.")

    def on_init_dependencies(self):
        dependencies = super().on_init_dependencies()
        dependencies += self.PROCESSORS_REGISTRY.values()
        return dependencies

    def _init_workers(self) -> list[mode.ServiceT]:
        workers = []
        for p in self.PROCESSORS_REGISTRY.values():
            if self._with_webapp:
                # FIXME: Perhaps only one Notify is suffisent ? It can be interesting
                #  to consider if we are sure of less traffic between workers and notifier.
                p.notifier = Notifier(
                    loop=self.loop,
                    host=self._web_app_host,
                    port=self._web_app_port,
                    scheme="http",
                )
            # Share the same event loop between all dependencies so that we will not experiment wired
            # behaviors due to each dependency runs on it own event loop.
            p.loop = self.loop
            p._delete = self._delete
            workers.append(p)

        return workers

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
                destination = self._search_destination(filename, config, supported)

                if not destination or filename in collected:
                    continue

                collected.append(filename)
                msg = self.create_message(filename, destination)
                await self.unprocessed.put(msg)
                self.logger.debug(f"File {filename} is appended to be processed")

    @functools.cached_property
    def server(self):
        return WebServer(
            loop=self.loop,
            host=self._web_app_host,
            port=self._web_app_port,
            db=self._db,
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

                # FIXME: find_destination should be moved to config service.
                destination = self._search_destination(filename, config=config)

                if not destination:
                    continue

                msg = self.create_message(filename, destination)
                await self.unprocessed.put(msg)
                self.logger.info(f"The file {filename} is received.")

    @mode.Service.task
    async def _provide(self):
        while not self.should_stop:
            message = await self.unprocessed.get()
            await self._router.route(message)
            self.unprocessed.task_done()
            await self.sleep(1.0)

    @staticmethod
    def create_message(filename, destination):
        return create_message(filename, destination)

    def _search_destination(self, filename: PATH, config=None, mapping=None) -> PATH:
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

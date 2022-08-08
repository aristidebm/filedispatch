import os.path
import logging
from typing import Union, Tuple
from pathlib import Path
from asyncio import Queue
from shutil import move

import mode
from watchfiles import awatch, Change
import os.path

from .config import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PATH = Union[str, Path]


class FileDispatch(mode.Service):
    def __init__(self, config: Settings):
        super().__init__()
        self.config = config
        self.unprocessed: Queue[Tuple[PATH, PATH]] = Queue()

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
                logger.debug(f"File {filename} is appended to be processed")

    @mode.Service.task
    async def _watch(self, config=None):
        config = config or self.config
        async for changes in awatch(config.source):
            for change in changes:
                # consider only adds, ignore all other changes.
                if Change.added not in change:
                    continue

                filename = change[1]
                # Ignore files added in config.source subdirectories since watchfiles do recursive watch
                # An issue is opened to fix that here https://github.com/samuelcolvin/watchfiles/issues/178
                if os.path.basename(os.path.dirname(filename)) != os.path.basename(
                    config.source
                ):
                    continue

                dest = self._find_destination(filename, config=config)

                if not dest:
                    continue

                await self.unprocessed.put((filename, dest))
                logger.info(f"File {filename} is appended to be processed")

    @mode.Service.task
    async def _process(self):
        while True:
            file_ = await self.unprocessed.get()
            self._move(*file_)
            self.unprocessed.task_done()

    def _move(self, filename: PATH, dest: PATH):
        try:
            # See hereh wy we choose it over os.rename os.rename
            # https://www.codespeedy.com/difference-between-os-rename-and-shutil-move-in-python/
            basename = os.path.basename(filename)
            move(filename, os.path.join(dest, basename))
        except OSError as exp:
            logger.exception(exp)

        logger.info(f"File {filename} moved to {dest}")

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
            logger.exception(exp)
            return

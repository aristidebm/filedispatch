import asyncio
import os.path
from tempfile import NamedTemporaryFile
from pathlib import Path

import pytest
from src.core import FileDispatch
from src.config import Config


def create_file(filesystem, ext="txt"):
    source = os.path.join(filesystem.name, "mnt")
    ext = ext.lower().removeprefix(".")
    ext = "." + ext
    f = NamedTemporaryFile(mode="w+b", suffix=ext, dir=source)
    return f


def contains(folder, file):
    return os.path.basename(file) in os.listdir(folder)


@pytest.fixture
def config(configfile, filesystem):
    conf = Config(config=configfile.name)()
    yield conf


@pytest.mark.asyncio
@pytest.mark.dispatcher
async def test_file_dispatch_success(mocker, config, filesystem):
    queue_put = mocker.patch("src.core.Queue.put")
    move = mocker.patch("src.core.move")
    logger = mocker.patch("src.core.logger.exception")

    async with FileDispatch(config=config) as dispatcher:
        await asyncio.sleep(1)

        assert dispatcher.unprocessed.empty()
        filename = create_file(filesystem, ext="mp4")

        await asyncio.sleep(1)

        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        queue_put.assert_awaited_once()
        # Make sure the file is moved
        move.assert_called_once()
        # Make sure an exception is not thrown
        logger.assert_not_called()

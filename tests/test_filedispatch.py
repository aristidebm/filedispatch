import asyncio
import os.path
import stat
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
async def test_file_task_producer_success(mocker, config, filesystem):
    queue_put = mocker.patch("src.core.Queue.put")

    async with FileDispatch(config=config) as dispatcher:
        await asyncio.sleep(1)

        assert dispatcher.unprocessed.empty()
        filename = create_file(filesystem, ext="mp4")
        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        queue_put.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.dispatcher
async def test_local_storage_consuming_success(mocker, config, filesystem):
    process = mocker.patch("src.core.LocalStorageProcessor.process")

    async with FileDispatch(config=config) as dispatcher:
        await asyncio.sleep(1)

        assert dispatcher.unprocessed.empty()
        filename = create_file(filesystem, ext="mp4")
        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        process.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.dispatcher
async def test_local_storage_consuming_failure_for_permissions(
    mocker, config, filesystem
):
    logger = mocker.patch("src.processors.logger.exception")

    async with FileDispatch(config=config) as dispatcher:
        await asyncio.sleep(1)

        assert dispatcher.unprocessed.empty()
        mode = 0o000
        assert stat.filemode(mode) == "?---------"
        os.chmod(Path(filesystem.name) / "mnt" / "video", mode)
        filename = create_file(filesystem, ext="mp4")
        assert contains(Path(filesystem.name) / "mnt", filename.name)
        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        logger.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.dispatcher
async def test_producer_collector(mocker, config, filesystem):
    queue_put = mocker.patch("src.core.Queue.put")

    await asyncio.sleep(1)

    filename = create_file(filesystem, ext="mp4")
    assert contains(Path(filesystem.name) / "mnt", filename.name)

    await asyncio.sleep(1)

    async with FileDispatch(config=config):
        # Make sure the file is added to the processing queue
        queue_put.assert_called_once()

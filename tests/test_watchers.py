import asyncio
import os.path
import stat
import tempfile
from pathlib import Path


import pytest
from src.watchers import FileWatcher


from .base import contains

pytestmark = pytest.mark.watcher


@pytest.mark.asyncio
async def test_new_files_are_queued(mocker, config, filesystem, new_file):
    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()
        dir_ = Path(filesystem.name) / "mnt"
        filename = new_file(dir_, suffix="mp4")
        assert contains(dir_, filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        queue_put.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_files_are_queued(mocker, config, filesystem, new_file):
    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    await asyncio.sleep(1)

    dir_ = Path(filesystem.name) / "mnt"
    filename = new_file(dir_, suffix="mp4")
    assert contains(dir_, filename.name)

    await asyncio.sleep(1)

    async with FileWatcher(config=config):
        # Make sure the file is added to the processing queue
        queue_put.assert_called_once()


@pytest.mark.asyncio
async def test_ignore_new_directories_and_symlinks(
    mocker, config, filesystem, new_file
):

    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()

        dir_ = Path(filesystem.name) / "mnt"
        filename = new_file(dir_)
        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        queue_put.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignore_source_subdirectories_changes(
    mocker, config, filesystem, new_file
):

    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()

        dir_ = Path(filesystem.name) / "mnt" / "video"
        filename = new_file(dir_, suffix="mp4")
        assert contains(dir_, filename.name)

        await asyncio.sleep(1)
        # Make sure the file is added to the processing queue
        queue_put.assert_not_awaited()

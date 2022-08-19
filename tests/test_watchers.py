import asyncio
import os.path
import stat
import tempfile
from pathlib import Path


import pytest
from src.watchers import FileWatcher


from .base import create_file, contains

pytestmark = pytest.mark.watcher


@pytest.mark.asyncio
async def test_new_files_are_queued(mocker, config, filesystem):
    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()
        filename = create_file(filesystem, ext="mp4")
        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        queue_put.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_files_are_queued(mocker, config, filesystem):
    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    await asyncio.sleep(1)

    filename = create_file(filesystem, ext="mp4")
    assert contains(Path(filesystem.name) / "mnt", filename.name)

    await asyncio.sleep(1)

    async with FileWatcher(config=config):
        # Make sure the file is added to the processing queue
        queue_put.assert_called_once()


@pytest.mark.asyncio
async def test_ignore_new_directories_and_symlinks(mocker, config, filesystem):

    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()
        filename = create_file(filesystem, is_file=False)
        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        queue_put.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignore_source_subdirectories_changes(mocker, config, filesystem):

    queue_put = mocker.patch("src.watchers.Queue.put")
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()

        subdir = Path(filesystem.name) / "mnt" / "video"
        with tempfile.NamedTemporaryFile(
            mode="w+b", suffix="mp4", dir=subdir
        ) as filename:

            assert contains(subdir, filename.name)
            await asyncio.sleep(1)
            # Make sure the file is added to the processing queue
            queue_put.assert_not_awaited()

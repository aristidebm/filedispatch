import asyncio
import stat
import pytest
import os
from pathlib import Path


from src.watchers import FileWatcher
from src.api.models import StatusEnum, LogEntry

from .base import contains, make_app


pytestmark = pytest.mark.process


class TestLocalStorageProcessor:
    @pytest.mark.asyncio
    async def test_local_storage_processor_acquire_the_file(
        self, mocker, config, filesystem, new_file
    ):
        acquire = mocker.patch("src.processors.LocalStorageProcessor.acquire")
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
            acquire.assert_awaited_once()

    # @pytest.mark.skip("fail for non determinated error yet")
    @pytest.mark.asyncio
    async def test_local_storage_processor_permissions_failure(
        self, mocker, config, filesystem, new_file
    ):
        logger = mocker.patch("src.processors.LocalStorageProcessor.logger.exception")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()
            mode = 0o000
            dir_ = Path(filesystem.name) / "mnt"

            assert stat.filemode(mode) == "?---------"
            os.chmod(dir_ / "video", mode)

            filename = new_file(dir_, suffix="mp4")
            assert contains(dir_, filename.name)

            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            logger.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_storage_processor_process_the_file(
        self, mocker, config, filesystem, new_file
    ):
        move = mocker.patch("src.processors.LocalStorageProcessor._move")
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
            move.assert_awaited_once()

    # @pytest.mark.skip("fail in test suite but not when executed alone")
    @pytest.mark.asyncio
    async def test_local_storage_processor_generated_payload(
        self, mocker, config, filesystem, new_file
    ):

        notify = mocker.patch("src.processors.LocalStorageProcessor._notify")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()

            dir_ = Path(filesystem.name) / "mnt"
            video = dir_ / "video"
            filename = new_file(dir_, suffix="mp4")
            assert contains(dir_, filename.name)

            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            notify.assert_awaited_once()

            # Test generated payload
            processor = watcher.PROCESSORS_REGISTRY["file"]
            payload = await processor._get_payload(
                filename.name, video, StatusEnum.SUCCEEDED
            )
            assert payload.get("id")
            assert payload.get("filename") == os.path.basename(filename.name)
            assert payload.get("extension") == "mp4"
            assert payload.get("source") == os.path.dirname(filename.name)
            assert payload.get("destination") == str(video)
            assert payload.get("processor") == processor.fancy_name.upper()
            assert payload.get("protocol") == "file"
            assert payload.get("size")
            assert not payload.get("reason")

            # FIXME: Test the generated logs in case of failure.


class TestHttpStorageProcessor:
    @pytest.mark.asyncio
    async def test_http_storage_processor_acquire_the_file(
        self, mocker, config, filesystem, new_file
    ):
        acquire = mocker.patch("src.processors.HttpStorageProcessor.acquire")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()

            dir_ = Path(filesystem.name) / "mnt"
            filename = new_file(dir_, suffix="mp3")
            assert contains(dir_, filename.name)

            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            acquire.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.process
    async def test_http_storage_processor_server_down_failure(
        self, mocker, config, filesystem, new_file, aiohttp_server
    ):
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")
        PORT = 8000

        await aiohttp_server(make_app(status=500), port=PORT)

        async with FileWatcher(config=config, port=PORT) as watcher:

            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()

            dir_ = Path(filesystem.name) / "mnt"
            filename = new_file(dir_, suffix="mp3")
            assert contains(dir_, filename.name)

            await asyncio.sleep(1)

            debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_storage_process_the_file(
        self, mocker, config, filesystem, new_file, aiohttp_server
    ):
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")

        PORT = 8000
        await aiohttp_server(make_app(), port=PORT)

        async with FileWatcher(config, port=PORT) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()

            dir_ = Path(filesystem.name) / "mnt"
            filename = new_file(dir_, suffix="mp3")
            assert contains(dir_, filename.name)

            await asyncio.sleep(1)

            debug.assert_not_called()

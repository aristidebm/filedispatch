import asyncio
import stat
import pytest
import os
from pathlib import Path

import responses

from src.watchers import FileWatcher
from src.api.models import StatusEnum, LogEntry

from .base import create_file, contains


pytestmark = pytest.mark.process


class TestLocalStorageProcessor:
    @pytest.mark.asyncio
    async def test_local_storage_processor_acquire_the_file(
        self, mocker, config, filesystem
    ):
        acquire = mocker.patch("src.processors.LocalStorageProcessor.acquire")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()
            filename = create_file(filesystem, ext="mp4")
            assert contains(Path(filesystem.name) / "mnt", filename.name)

            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            acquire.assert_awaited_once()

    @pytest.mark.skip("fail for non determinated error yet")
    @pytest.mark.asyncio
    async def test_local_storage_processor_permissionrspss_failure(
        self, mocker, config, filesystem
    ):
        logger = mocker.patch("src.processors.LocalStorageProcessor.logger.exception")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()
            mode = 0o000
            assert stat.filemode(mode) == "?---------"
            os.chmod(Path(filesystem.name) / "mnt" / "video", mode)
            filename = create_file(filesystem, ext="mp4")
            assert contains(Path(filesystem.name) / "mnt", filename.name)
            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            logger.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_storage_processor_process_the_file(
        self, mocker, config, filesystem
    ):
        move = mocker.patch("src.processors.LocalStorageProcessor._move")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()
            filename = create_file(filesystem, ext="mp4")
            assert contains(Path(filesystem.name) / "mnt", filename.name)

            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            move.assert_awaited_once()

    @pytest.mark.skip("fail in test suite but not when executed alone")
    @pytest.mark.asyncio
    async def test_local_storage_processor_generated_payload(
        self, mocker, config, filesystem
    ):

        notify = mocker.patch("src.processors.LocalStorageProcessor._notify")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()
            filename = create_file(filesystem, ext="mp4")
            source = Path(filesystem.name) / "mnt"
            video = source / "video"
            assert contains(source, filename.name)

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


#
class TestHttpStorageProcessor:
    @pytest.mark.asyncio
    async def test_http_storage_processor_acquire_the_file(
        self, mocker, config, filesystem
    ):
        acquire = mocker.patch("src.processors.HttpStorageProcessor.acquire")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            assert watcher.unprocessed.empty()
            filename = create_file(filesystem, ext="mp3")
            assert contains(Path(filesystem.name) / "mnt", filename.name)

            await asyncio.sleep(1)

            # Make sure the file is added to the processing queue
            acquire.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.process
    async def test_http_storage_processor_server_down_failure(
        self, mocker, config, filesystem
    ):
        logger = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")
        async with FileWatcher(config=config) as watcher:
            await asyncio.sleep(1)

            with responses.RequestsMock() as rs:
                rs.add(
                    responses.POST,
                    "http://127.0.0.1:8000/documents/audio",
                    body=b"",
                    status=500,
                )
                assert watcher.unprocessed.empty()
                filename = create_file(filesystem, ext="mp3")
                # assert contains(Path(filesystem.name) / "mnt", filename.name)
                await asyncio.sleep(1)
                rs.assert_call_count("http://127.0.0.1:8000/documents/audio", 3)

            # Make sure the file is added to the processing queue
            logger.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_storage_process_the_file(
        self, mocker, config, filesystem, aiohttp_server
    ):
        # Mock the server to the prevent actual server launching when running tests
        mocker.patch("src.api.server.WebServer.run_app")

        PORT = 8000
        URL = f"http://127.0.0.1:{PORT}/documents/audio"

        async with FileWatcher(config, port=PORT) as watcher:
            await asyncio.sleep(1)

            with responses.RequestsMock() as rs:
                rs.add(
                    responses.POST,
                    URL,
                    body="Successfully uploaded",
                    status=200,
                )

                assert watcher.unprocessed.empty()
                filename = create_file(filesystem, ext="mp3")
                # assert contains(Path(filesystem.name) / "mnt", filename.name)
                rs.assert_call_count(URL, 1)

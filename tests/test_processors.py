import asyncio
import stat
import uuid

import pytest
import os
from pathlib import Path


from src.watchers import FileWatcher
from src.api.models import StatusEnum, LogEntry

from .base import contains, make_app


pytestmark = pytest.mark.process


class TestLocalStorageProcessor:
    @pytest.fixture(autouse=True)
    def mock_processors(self, mocker):
        # Mock background tasks (since their running forever and we are going to wait them manually)
        # spec=True, cause a check is done in library to make sure they are dealing with a ServiceTask
        mocker.patch("src.watchers.FileWatcher._watch", spec=True)
        mocker.patch("src.watchers.FileWatcher._provide", spec=True)
        mocker.patch("src.processors.HttpStorageProcessor._process", spec=True)
        mocker.patch("src.processors.FtpStorageProcessor._process", spec=True)
        mocker.patch("src.notifiers.Notifier._notify", spec=True)
        mocker.patch("aiofiles.os.path.isfile", returned_value=True)

    @pytest.mark.asyncio
    async def test_local_storage_processor_succeed_processing(
        self, mocker, config, filesystem, await_scheduled_task
    ):
        source = Path(filesystem.name) / "mnt"
        destination = source / "video"
        filename = source / f"tmp-{uuid.uuid4()}.mp4"

        mock_get = mocker.patch(
            "src.processors.Queue.get", side_effect=[(filename, destination)]
        )

        mock_copyfile = mocker.patch("src.processors.copyfile", returned_value=None)

        mock_notify = mocker.patch("src.processors.LocalStorageProcessor._notify")

        # For some reasons context manager is not working when we patch some the method
        # of the class, so we use the plain old manner.
        try:
            watcher = FileWatcher(config=config)
            await watcher.start()
            # run all waiting tasks.
            await await_scheduled_task()

            mock_get.assert_awaited()
            mock_copyfile.assert_awaited_once_with(
                Path(filename), str(destination / filename.name)
            )
            mock_notify.assert_awaited_once_with(
                Path(filename), Path(destination), StatusEnum.SUCCEEDED, delete=True
            )
        finally:
            await watcher.stop()

    @pytest.mark.asyncio
    async def test_local_storage_processor_permissions_failure(
        self, mocker, config, filesystem, await_scheduled_task
    ):
        logger = mocker.patch("src.processors.LocalStorageProcessor.logger.exception")

        source = Path(filesystem.name) / "mnt"
        destination = source / "video"
        filename = source / f"tmp-{uuid.uuid4()}.mp4"

        mock_get = mocker.patch(
            "src.processors.Queue.get", side_effect=[(filename, destination)]
        )

        reason = "PermissionError: Permission Denied"

        mock_copyfile = mocker.patch(
            "src.processors.copyfile",
            side_effect=PermissionError(reason),
        )

        mock_notify = mocker.patch("src.processors.LocalStorageProcessor._notify")

        # For some reasons context manager is not working when we patch some the method
        # of the class, so we use the plain old manner.
        try:
            watcher = FileWatcher(config=config)
            await watcher.start()
            # run all waiting tasks.
            await await_scheduled_task()

            mock_get.assert_awaited()
            mock_copyfile.assert_awaited_once_with(
                Path(filename), str(destination / filename.name)
            )

            # Make sure we log the exception.
            logger.assert_called_once()
            mock_notify.assert_awaited_once_with(
                Path(filename),
                Path(destination),
                StatusEnum.FAILED,
                reason,
            )
        finally:
            await watcher.stop()

    @pytest.mark.asyncio
    async def test_payload_is_sent_to_notifier(
        self, mocker, config, filesystem, await_scheduled_task
    ):

        source = Path(filesystem.name) / "mnt"
        destination = source / "video"
        filename = source / f"tmp-{uuid.uuid4()}.mp3"

        exception = mocker.patch(
            "src.processors.LocalStorageProcessor.logger.exception"
        )

        mock_copyfile = mocker.patch("src.processors.copyfile", returned_value=None)

        mock_get = mocker.patch(
            "src.processors.Queue.get", side_effect=[(filename, destination)]
        )

        notifier = mocker.MagicMock()
        mock_acquire = mocker.Mock(return_value=None)
        notifier.acquire = mock_acquire
        notifier.maybe_start = mocker.AsyncMock()
        notifier.stop = mocker.AsyncMock()
        mock = mocker.PropertyMock(return_value=notifier)

        mocker.patch(
            "src.processors.LocalStorageProcessor.notifier",
            new=mock,
        )

        try:
            watcher = FileWatcher(config=config)
            await watcher.start()

            await await_scheduled_task()
            mock_get.assert_awaited()
            mock_copyfile.assert_awaited_once_with(
                Path(filename), str(destination / filename.name)
            )
            exception.assert_not_called()
            mock_acquire.assert_called_once_with(mocker.ANY)
        finally:
            await watcher.stop()


class TestHttpStorageProcessor:
    @pytest.fixture(autouse=True)
    def mock_processors(self, mocker):
        # Mock background tasks (since their running forever and we are going to wait them manually)
        # spec=True, cause a check is done in library to make sure they are dealing with a ServiceTask
        mocker.patch("src.watchers.FileWatcher._watch", spec=True)
        mocker.patch("src.watchers.FileWatcher._provide", spec=True)
        mocker.patch("src.processors.LocalStorageProcessor._process", spec=True)
        mocker.patch("src.processors.FtpStorageProcessor._process", spec=True)
        mocker.patch("src.notifiers.Notifier._notify", spec=True)
        mocker.patch("aiofiles.os.path.isfile", returned_value=True)

    @pytest.mark.asyncio
    async def test_http_storage_processor_server_down_failure(
        self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
    ):

        PORT = 8000

        await aiohttp_server(make_app(status=500), port=PORT)

        source = Path(filesystem.name) / "mnt"
        destination = f"http://127.0.0.1:{PORT}/documents/audio"
        filename = source / f"tmp-{uuid.uuid4()}.mp3"

        debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")

        mock_get = mocker.patch(
            "src.processors.Queue.get", side_effect=[(filename, destination)]
        )

        mock_open = mocker.patch(
            "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
        )

        mock_notify = mocker.patch("src.processors.HttpStorageProcessor._notify")

        try:
            watcher = FileWatcher(config=config, port=PORT)
            await watcher.start()

            await await_scheduled_task()
            mock_get.assert_awaited()
            mock_open.assert_awaited_once_with(filename, "rb")

            debug.assert_called_once()

            mock_notify.assert_awaited_once_with(
                Path(filename),
                destination,
                StatusEnum.FAILED,
                mocker.ANY,
            )
        finally:
            await watcher.stop()

    @pytest.mark.asyncio
    async def test_http_storage_process_the_file(
        self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
    ):

        PORT = 8000

        await aiohttp_server(make_app(status=200), port=PORT)

        source = Path(filesystem.name) / "mnt"
        destination = f"http://127.0.0.1:{PORT}/documents/audio"
        filename = source / f"tmp-{uuid.uuid4()}.mp3"

        debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")

        mock_get = mocker.patch(
            "src.processors.Queue.get", side_effect=[(filename, destination)]
        )

        mock_open = mocker.patch(
            "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
        )

        mock_notify = mocker.patch("src.processors.HttpStorageProcessor._notify")

        try:
            watcher = FileWatcher(config=config, port=PORT)
            await watcher.start()

            await await_scheduled_task()
            mock_get.assert_awaited()
            mock_open.assert_awaited_once_with(filename, "rb")

            debug.assert_not_called()

            mock_notify.assert_awaited_once_with(
                Path(filename),
                destination,
                StatusEnum.SUCCEEDED,
            )
        finally:
            await watcher.stop()

    @pytest.mark.asyncio
    async def test_payload_is_sent_to_notifier(
        self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
    ):
        PORT = 8000

        await aiohttp_server(make_app(status=200), port=PORT)

        source = Path(filesystem.name) / "mnt"
        destination = f"http://127.0.0.1:{PORT}/documents/audio"
        filename = source / f"tmp-{uuid.uuid4()}.mp3"

        debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")

        mock_get = mocker.patch(
            "src.processors.Queue.get", side_effect=[(filename, destination)]
        )

        mock_open = mocker.patch(
            "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
        )

        notifier = mocker.MagicMock()
        mock_acquire = mocker.Mock(return_value=None)
        notifier.acquire = mock_acquire
        notifier.maybe_start = mocker.AsyncMock()
        notifier.stop = mocker.AsyncMock()
        mock = mocker.PropertyMock(return_value=notifier)

        mocker.patch(
            "src.processors.HttpStorageProcessor.notifier",
            new=mock,
        )

        try:
            watcher = FileWatcher(config=config, port=PORT)
            await watcher.start()

            await await_scheduled_task()
            mock_get.assert_awaited()
            mock_open.assert_awaited_once_with(filename, "rb")

            debug.assert_not_called()

            mock_acquire.assert_called_once_with(mocker.ANY)
        finally:
            await watcher.stop()


# FIXME: Add FtpServer test later.

# class TestFtpStorageProcessor:
#     @pytest.fixture(autouse=True)
#     def mock_processors(self, mocker):
#         # Mock background tasks (since their running forever and we are going to wait them manually)
#         # spec=True, cause a check is done in library to make sure they are dealing with a ServiceTask
#         mocker.patch("src.watchers.FileWatcher._watch", spec=True)
#         mocker.patch("src.watchers.FileWatcher._provide", spec=True)
#         mocker.patch("src.processors.LocalStorageProcessor._process", spec=True)
#         mocker.patch("src.processors.HttpStorageProcessor._process", spec=True)
#         mocker.patch("src.notifiers.Notifier._notify", spec=True)
#
#     @pytest.mark.asyncio
#     async def test_http_storage_processor_server_down_failure(
#         self, mocker, config, filesystem, await_scheduled_task
#     ):
#
#         PORT = 8000
#
#         await aiohttp_server(make_app(status=500), port=PORT)
#
#         source = Path(filesystem.name) / "mnt"
#         destination = f"http://127.0.0.1:{PORT}/documents/audio"
#         filename = source / f"tmp-{uuid.uuid4()}.mp3"
#
#         debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")
#
#         mock_get = mocker.patch(
#             "src.processors.Queue.get", side_effect=[(filename, destination)]
#         )
#
#         mock_open = mocker.patch(
#             "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
#         )
#
#         mock_notify = mocker.patch("src.processors.HttpStorageProcessor._notify")
#
#         try:
#             watcher = FileWatcher(config=config, port=PORT)
#             await watcher.start()
#
#             await await_scheduled_task()
#             mock_get.assert_awaited()
#             mock_open.assert_awaited_once_with(filename, "rb")
#
#             debug.assert_called_once()
#
#             mock_notify.assert_awaited_once_with(
#                 Path(filename),
#                 destination,
#                 StatusEnum.FAILED,
#                 mocker.ANY,
#             )
#         finally:
#             await watcher.stop()

# @pytest.mark.asyncio
# async def test_http_storage_process_the_file(
#         self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
# ):
#
#     PORT = 8000
#
#     await aiohttp_server(make_app(status=200), port=PORT)
#
#     source = Path(filesystem.name) / "mnt"
#     destination = f"http://127.0.0.1:{PORT}/documents/audio"
#     filename = source / f"tmp-{uuid.uuid4()}.mp3"
#
#     debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")
#
#     mock_get = mocker.patch(
#         "src.processors.Queue.get", side_effect=[(filename, destination)]
#     )
#
#     mock_open = mocker.patch(
#         "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
#     )
#
#     mock_notify = mocker.patch("src.processors.HttpStorageProcessor._notify")
#
#     try:
#         watcher = FileWatcher(config=config, port=PORT)
#         await watcher.start()
#
#         await await_scheduled_task()
#         mock_get.assert_awaited()
#         mock_open.assert_awaited_once_with(filename, "rb")
#
#         debug.assert_not_called()
#
#         mock_notify.assert_awaited_once_with(
#             Path(filename),
#             destination,
#             StatusEnum.SUCCEEDED,
#         )
#     finally:
#         await watcher.stop()
#
# @pytest.mark.asyncio
# async def test_payload_is_sent_to_notifier(
#         self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
# ):
#     PORT = 8000
#
#     await aiohttp_server(make_app(status=200), port=PORT)
#
#     source = Path(filesystem.name) / "mnt"
#     destination = f"http://127.0.0.1:{PORT}/documents/audio"
#     filename = source / f"tmp-{uuid.uuid4()}.mp3"
#
#     debug = mocker.patch("src.processors.HttpStorageProcessor.logger.debug")
#
#     mock_get = mocker.patch(
#         "src.processors.Queue.get", side_effect=[(filename, destination)]
#     )
#
#     mock_open = mocker.patch(
#         "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
#     )
#
#     notifier = mocker.MagicMock()
#     mock_acquire = mocker.Mock(return_value=None)
#     notifier.acquire = mock_acquire
#     notifier.maybe_start = mocker.AsyncMock()
#     notifier.stop = mocker.AsyncMock()
#     mock = mocker.PropertyMock(return_value=notifier)
#
#     mocker.patch(
#         "src.processors.HttpStorageProcessor.notifier",
#         new=mock,
#     )
#
#     try:
#         watcher = FileWatcher(config=config, port=PORT)
#         await watcher.start()
#
#         await await_scheduled_task()
#         mock_get.assert_awaited()
#         mock_open.assert_awaited_once_with(filename, "rb")
#
#         debug.assert_not_called()
#
#         mock_acquire.assert_called_once_with(mocker.ANY)
#     finally:
#         await watcher.stop()

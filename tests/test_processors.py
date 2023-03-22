import io
import uuid
from unittest import mock

import aiofiles
import aioftp
import pytest

from src.processors import (
    LocalStorageProcessor,
    HttpStorageProcessor,
    FtpStorageProcessor,
)
from src.utils import StatusEnum


pytestmark = pytest.mark.process


def get_notifier_mock():
    notifier = mock.MagicMock()
    notifier.acquire = mock.Mock()
    notifier.maybe_start = mock.AsyncMock()
    notifier.stop = mock.AsyncMock()
    return mock.PropertyMock(return_value=notifier)


class TestLocalStorageProcessor:
    @pytest.mark.asyncio
    async def test_local_storage_processing_succeeded(
        self, mocker, await_scheduled_task
    ):
        sut = LocalStorageProcessor()
        filename, destination = "filename.mp4", "/tmp/destination"
        copyfile = mocker.patch("src.processors.copyfile")
        notify = mocker.patch("src.processors.LocalStorageProcessor._notify")
        await sut.process(filename, destination)
        copyfile.assert_awaited_once()
        assert copyfile.await_args[0] == (
            filename,
            f"{destination}/{filename}",
        )
        await await_scheduled_task()
        notify.assert_awaited_once()
        assert notify.await_args[0] == (
            filename,
            destination,
            StatusEnum.SUCCEEDED,
        )

    @pytest.mark.asyncio
    async def test_local_processing_failed_for_lack_of_permissions(
        self, mocker, await_scheduled_task
    ):
        sut = LocalStorageProcessor()
        filename, destination = "filename.mp4", "/tmp/destination"
        reason = "PermissionError: Permission Denied"
        copyfile = mocker.patch(
            "src.processors.copyfile", side_effect=PermissionError(reason)
        )
        notify = mocker.patch("src.processors.LocalStorageProcessor._notify")

        await sut.process(filename, destination)

        copyfile.assert_awaited_once_with(
            filename,
            f"{destination}/{filename}",
        )

        await await_scheduled_task()

        notify.assert_awaited_once_with(
            filename, destination, StatusEnum.FAILED, reason
        )

    @pytest.mark.asyncio
    async def test_payload_is_sent_to_notifier(self, mocker, await_scheduled_task):
        sut = LocalStorageProcessor()
        filename, destination = "filename.mp4", "/tmp/destination"
        mocker.patch("src.processors.copyfile")
        mocker.patch(
            "src.processors.LocalStorageProcessor.notifier", new=get_notifier_mock()
        )
        await sut.process(filename, destination)
        await await_scheduled_task()
        sut.notifier.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_remove_file_from_origin(self, mocker, await_scheduled_task):
        sut = LocalStorageProcessor()
        filename, destination = "filename.mp4", "/tmp/destination"
        mocker.patch("src.processors.copyfile")
        mocker.patch(
            "src.processors.LocalStorageProcessor.notifier", new=get_notifier_mock()
        )
        unlink = mocker.patch("src.processors.unlink")
        await sut.process(filename, destination, delete=True)
        await await_scheduled_task()
        unlink.assert_awaited_once_with(filename)


class TestHttpStorageProcessor:
    @pytest.mark.asyncio
    async def test_http_storage_processing_succeeded(
        self, mocker, await_scheduled_task
    ):
        # Arrange
        sut = HttpStorageProcessor()
        filename, destination = "filename.mp4", "https://server/documents/videos"

        # Mocks
        send = mocker.patch("src.processors.RetryClient.post")
        send.return_value.__aenter__.return_value.ok = True
        writer = mocker.patch("src.processors.aiohttp.MultipartWriter")
        writer_obj = writer.return_value.__enter__.return_value
        writer_obj.append = mocker.MagicMock()
        notify = mocker.patch("src.processors.HttpStorageProcessor._notify")
        content = io.StringIO()
        mock_open = mocker.patch(
            "src.processors.aiofiles.open", new=mocker.AsyncMock(side_effect=[content])
        )

        # Act
        await sut.process(filename, destination)

        # Assert
        mock_open.assert_awaited_once_with(filename, "rb")
        writer_obj.append.assert_called_once_with(content)
        await await_scheduled_task()
        notify.assert_awaited_once_with(filename, destination, StatusEnum.SUCCEEDED)

    @pytest.mark.asyncio
    async def test_should_log_failure_when_error_occurred_while_sending_file_on_destination_server(
        self, mocker, await_scheduled_task
    ):
        # Arrange
        sut = HttpStorageProcessor()
        filename, destination = "filename.mp4", "https://server/documents/videos"

        # Mocks
        send = mocker.patch("src.processors.RetryClient.post")
        send.return_value.__aenter__.return_value.ok = False
        writer = mocker.patch("src.processors.aiohttp.MultipartWriter")
        writer_obj = writer.return_value.__enter__.return_value
        writer_obj.append = mocker.MagicMock()
        notify = mocker.patch("src.processors.HttpStorageProcessor._notify")
        content = io.StringIO()
        mock_open = mocker.patch(
            "src.processors.aiofiles.open", new=mocker.AsyncMock(side_effect=[content])
        )

        # Act
        await sut.process(filename, destination)

        # Assert
        mock_open.assert_awaited_once_with(filename, "rb")
        writer_obj.append.assert_called_once_with(content)
        await await_scheduled_task()
        notify.assert_awaited_once_with(
            filename, destination, StatusEnum.FAILED, mocker.ANY
        )

    @pytest.mark.asyncio
    async def test_should_log_failure_when_unable_to_read_the_source_file(
        self, mocker, await_scheduled_task
    ):
        # Arrange
        sut = HttpStorageProcessor()
        filename, destination = "filename.mp4", "https://server/documents/videos"
        reason = "PermissionError: Permission Denied"

        # Mocks
        send = mocker.patch("src.processors.RetryClient.post")
        send.return_value.__aenter__.return_value.ok = True
        writer = mocker.patch("src.processors.aiohttp.MultipartWriter")
        writer_obj = writer.return_value.__enter__.return_value
        writer_obj.append = mocker.MagicMock()
        notify = mocker.patch("src.processors.HttpStorageProcessor._notify")
        mock_open = mocker.patch(
            "src.processors.aiofiles.open",
            new=mocker.AsyncMock(side_effect=[PermissionError(reason)]),
        )

        # Act
        await sut.process(filename, destination)

        # Assert
        mock_open.assert_awaited_once_with(filename, "rb")
        writer_obj.append.assert_not_called()
        await await_scheduled_task()
        notify.assert_awaited_once_with(
            filename,
            destination,
            StatusEnum.FAILED,
            "PermissionError: Permission Denied",
        )

    @pytest.mark.asyncio
    async def test_payload_is_sent_to_notifier(
        self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
    ):
        # Arrange
        sut = HttpStorageProcessor()
        filename, destination = "filename.mp4", "https://server/documents/videos"

        # Mocks
        send = mocker.patch("src.processors.RetryClient.post")
        send.return_value.__aenter__.return_value.ok = True
        writer = mocker.patch("src.processors.aiohttp.MultipartWriter")
        writer_obj = writer.return_value.__enter__.return_value
        writer_obj.append = mocker.MagicMock()
        content = io.StringIO()
        mocker.patch(
            "src.processors.aiofiles.open", new=mocker.AsyncMock(side_effect=[content])
        )
        mocker.patch(
            "src.processors.HttpStorageProcessor.notifier", new=get_notifier_mock()
        )

        # Act
        await sut.process(filename, destination)
        await await_scheduled_task()

        # Assert
        sut.notifier.acquire.assert_called_once()


class TestFtpStorageProcessor:
    @pytest.mark.asyncio
    async def test_ftp_storage_processing_succeeded(self, mocker, await_scheduled_task):
        # Arrange
        sut = FtpStorageProcessor()
        filename, destination = (
            "filename.mp4",
            "ftp://username:password@ftp.foo.org/home/user/videos",
        )

        # Mocks
        uploader = mocker.patch("aioftp.Client.context")
        uploader_obj = uploader.return_value.__aenter__.return_value
        uploader_obj.upload = mocker.AsyncMock()
        notify = mocker.patch("src.processors.FtpStorageProcessor._notify")

        # Act
        await sut.process(filename, destination)
        uploader_obj.upload.assert_awaited_once_with(filename, destination)
        await await_scheduled_task()
        notify.assert_awaited_once_with(filename, destination, StatusEnum.SUCCEEDED)

    @pytest.mark.asyncio
    async def test_should_log_failure_when_error_occurred_while_sending_file_on_destination_server(
        self, mocker, await_scheduled_task
    ):
        # Arrange
        sut = FtpStorageProcessor()
        filename, destination = (
            "filename.mp4",
            "ftp://username:password@ftp.foo.org/home/user/videos",
        )

        # Mocks
        uploader = mocker.patch("aioftp.Client.context")
        uploader_obj = uploader.return_value.__aenter__.return_value
        uploader_obj.upload = mocker.AsyncMock(side_effect=[aioftp.AIOFTPException()])
        notify = mocker.patch("src.processors.FtpStorageProcessor._notify")

        # Act
        await sut.process(filename, destination)
        uploader_obj.upload.assert_awaited_once_with(filename, destination)
        await await_scheduled_task()
        notify.assert_awaited_once_with(
            filename, destination, StatusEnum.FAILED, mocker.ANY
        )

    @pytest.mark.asyncio
    async def test_payload_is_sent_to_notifier(self, mocker, await_scheduled_task):
        # Arrange
        sut = FtpStorageProcessor()
        filename, destination = (
            "filename.mp4",
            "ftp://username:password@ftp.foo.org/home/user/videos",
        )

        # Mocks
        uploader = mocker.patch("aioftp.Client.context")
        uploader_obj = uploader.return_value.__aenter__.return_value
        uploader_obj.upload = mocker.AsyncMock()

        mocker.patch(
            "src.processors.FtpStorageProcessor.notifier", new=get_notifier_mock()
        )

        await sut.process(filename, destination)
        uploader_obj.upload.assert_awaited_once_with(filename, destination)
        await await_scheduled_task()
        sut.notifier.acquire.assert_called_once()

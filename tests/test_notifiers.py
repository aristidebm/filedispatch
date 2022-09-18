import asyncio
import uuid

import pytest
from pathlib import Path

from src.utils import StatusEnum
from src.watchers import FileWatcher

from .base import make_app

pytestmark = pytest.mark.notif


@pytest.fixture(autouse=True)
def mock_processors(self, mocker):
    # Mock background tasks (since their running forever and we are going to wait them manually)
    # spec=True, cause a check is done in library to make sure they are dealing with a ServiceTask
    mocker.patch("src.watchers.FileWatcher._watch", spec=True)
    mocker.patch("src.watchers.FileWatcher._provide", spec=True)
    mocker.patch("src.processors.HttpStorageProcessor._process", spec=True)
    mocker.patch("src.processors.LocalStorageProcessor._process", spec=True)
    mocker.patch("src.processors.FtpStorageProcessor._process", spec=True)
    # mocker.patch("src.notifiers.Notifier._notify", spec=True)
    mocker.patch("aiofiles.os.path.isfile", returned_value=True)


# # @pytest.mark.skip("fail for non determinate error yet")
# @pytest.mark.asyncio
# async def test_notifier_send_log_to_web_app(
#     self, mocker, config, filesystem, aiohttp_server, await_scheduled_task
# ):
#     PORT = 8000
#
#     await aiohttp_server(make_app(status=200), port=PORT)
#
#     mocker.patch("src.notifiers.Notifier.acquire")
#
#     source = Path(filesystem.name) / "mnt"
#     destination = "/home/documents/audio"
#     filename = source / f"tmp-{uuid.uuid4()}.mp4"
#
#     debug = mocker.patch("src.processors.LocalStorageProcessor.logger.debug")
#
#     mock_get = mocker.patch(
#         "src.processors.Queue.get", side_effect=[(filename, destination)]
#     )
#
#     mock_open = mocker.patch(
#         "src.processors.aiofiles.open", new_callable=mocker.AsyncMock
#     )
#
#     async with FileWatcher(config=config):
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

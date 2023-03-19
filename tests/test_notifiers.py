import pytest

from aiohttp import hdrs
from aiohttp.web_routedef import RouteDef

from src.watchers import FileWatcher

from .base import make_app

pytestmark = pytest.mark.notif

# FIXME: Instead mocking all this services (it means, we don't need them to run)
#  a better way of doing things is to manually each service wihout and make sure
#  it do what expected it to do.


@pytest.fixture(autouse=True)
def mock_consumeors(mocker):
    # Mock background tasks (since their running forever and we are going to wait them manually)
    # spec=True, cause a check is done in library to make sure they are dealing with a ServiceTask
    mocker.patch("src.watchers.FileWatcher._watch", spec=True)
    mocker.patch("src.watchers.FileWatcher._provide", spec=True)
    mocker.patch("src.processors.BaseProcessor._consume", spec=True)
    # mocker.patch("src.processors.LocalStorageProcessor._consume", spec=True)
    # mocker.patch("src.processors.FtpStorageProcessor._consume", spec=True)
    mocker.patch("src.processors.HttpStorageProcessor._consume", spec=True)
    mocker.patch("src.processors.LocalStorageProcessor._consume", spec=True)
    mocker.patch("src.processors.FtpStorageProcessor._consume", spec=True)
    mocker.patch("src.processors.HttpStorageProcessor.on_start", spec=True)
    mocker.patch("src.processors.FtpStorageProcessor.on_start", spec=True)
    mocker.patch("aiofiles.os.path.isfile", returned_value=True)


@pytest.mark.asyncio
async def test_notifier_send_log_to_web_app(
    mocker, config, aiohttp_server, await_scheduled_task
):
    PORT = 8000

    mocker.patch("src.notifiers.Notifier.logger.debug")
    mocker.patch("src.processors.Queue.get")
    mocker.patch("src.processors.aiofiles.open")

    payload = {
        "source": "/storage/",
        "filename": "/storage/example.mp4",
        "destination": "/storage/audio/",
        "processor": "LOCAL STORAGE PROCESSOR",
        "extension": "mp3",
        "protocol": "file",
        "status": "SUCCEEDED",
        "size": "18 MB",
        "byte_size": "18874368",
    }

    handler = mocker.AsyncMock(return_value=payload)

    route = RouteDef(
        method=hdrs.METH_POST,
        path="/api/v1/logs",
        handler=handler,
        kwargs={},
    )

    await aiohttp_server(make_app(routes=[route], status=201), port=PORT)

    mock_get = mocker.patch("src.notifiers.Queue.get", side_effect=[payload])
    mock_debug = mocker.patch("src.notifiers.Notifier.logger.debug")

    async with FileWatcher(config=config, port=PORT):
        await await_scheduled_task()
        mock_get.assert_awaited()
        handler.assert_awaited_once()
        mock_debug.assert_called_once()

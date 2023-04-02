import pytest

from src.notifiers import Notifier

pytestmark = pytest.mark.notif


@pytest.mark.asyncio
async def test_notifier_successfully_send_logs_to_webapp(mocker):
    sut = Notifier(url="http://127.0.0.1:8000/api/v1/logs/")
    sut._handle_failure = mocker.AsyncMock()

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

    send = mocker.patch("src.notifiers.RetryClient.post")
    send.return_value.__aenter__.return_value.ok = True
    await sut.notify(payload)
    sut._handle_failure.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_handle_webapp_failures(mocker):
    sut = Notifier(url="http://127.0.0.1:8000/api/v1/logs/")
    sut._handle_failure = mocker.AsyncMock()

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

    send = mocker.patch("src.notifiers.RetryClient.post")
    send.return_value.__aenter__.return_value.ok = False
    await sut.notify(payload)
    sut._handle_failure.assert_called_once()

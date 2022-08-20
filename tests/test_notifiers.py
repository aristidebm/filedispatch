import asyncio
import pytest
from pathlib import Path

from src.watchers import FileWatcher

from .base import create_file, contains


pytestmark = pytest.mark.notif


# @pytest.mark.skip("fail for non determinate error yet")
@pytest.mark.asyncio
async def test_notifier_acquire_the_file(mocker, config, filesystem):
    # Mock the server to the prevent actual server launching when running tests
    mocker.patch("src.api.server.WebServer.run_app")

    acquire = mocker.patch("src.notifiers.Notifier.acquire")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()
        filename = create_file(filesystem, ext="mp4")
        assert contains(Path(filesystem.name) / "mnt", filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        acquire.assert_awaited_once()

import asyncio
import pytest
from pathlib import Path

from src.watchers import FileWatcher

from .base import contains


pytestmark = pytest.mark.notif


# @pytest.mark.skip("fail for non determinate error yet")
@pytest.mark.asyncio
async def test_notifier_acquire_the_file(mocker, config, filesystem, new_file):
    acquire = mocker.patch("src.notifiers.Notifier.acquire")

    async with FileWatcher(config=config) as watcher:
        await asyncio.sleep(1)

        assert watcher.unprocessed.empty()

        dir_ = Path(filesystem.name) / "mnt"
        filename = new_file(dir_, suffix="mp3")
        assert contains(dir_, filename.name)

        await asyncio.sleep(1)

        # Make sure the file is added to the processing queue
        acquire.assert_called_once()

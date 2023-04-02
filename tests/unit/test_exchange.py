import asyncio
from watchfiles import Change

import pytest
from src.exchange import FileWatcher

pytestmark = pytest.mark.watcher


@pytest.fixture
def mock_isfile(mocker):
    def _inner_fun(**kwargs):
        mocker.patch("aiofiles.os.path.isfile", **kwargs)

    return _inner_fun


class TestWatch:
    @pytest.mark.asyncio
    async def test_should_collect_unprocessed_files_on_starting(self, mocker, config):
        sut = FileWatcher(config=config)
        sut._collect_unprocessed = mocker.AsyncMock()
        async with sut:
            sut._collect_unprocessed.assert_awaited_once_with(config=config)

    @pytest.mark.asyncio
    async def test_should_process_new_added_files(self, mocker, config, mock_awatch):
        sut = FileWatcher(config=config)
        queue_put = mocker.patch("src.exchange.Queue.put")
        mocker.patch("src.exchange.aiofiles.os.path.isfile", side_effect=[True])
        filename = f"{str(config.source).removesuffix('/')}/filename.mp4"
        changes = {(Change.added, filename)}
        mock_awatch(changes)

        async with sut:
            await asyncio.sleep(0)
            queue_put.asset_awaited_once()
            message = queue_put.await_args.args[0]
            assert message.body.get("filename") == filename

    @pytest.mark.asyncio
    async def test_should_ignore_directories_and_symlinks(
        self, mocker, config, mock_awatch
    ):
        sut = FileWatcher(config=config)
        queue_put = mocker.patch("src.exchange.Queue.put")
        mocker.patch("src.exchange.aiofiles.os.path.isfile", side_effect=[False])

        filename = f"{str(config.source).removesuffix('/')}/filename.mp4"
        changes = {(Change.added, filename)}

        mock_awatch(changes)
        async with sut:
            await asyncio.sleep(0)
            queue_put.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_perform_shallow_watching(self, config, mocker, mock_awatch):
        sut = FileWatcher(config=config)
        queue_put = mocker.patch("src.exchange.Queue.put")
        mocker.patch("src.exchange.aiofiles.os.path.isfile", side_effect=[True])
        filename = f"{str(config.source).removesuffix('/')}/subdirectory/filename.mp4"
        changes = {(Change.added, filename)}

        mock_awatch(changes)
        async with sut:
            await asyncio.sleep(0)
            queue_put.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_route_changes_to_the_right_processors(
        self, config, mocker, mock_awatch
    ):
        sut = FileWatcher(config=config)
        processor1 = sut.PROCESSORS_REGISTRY["file"]
        processor2 = sut.PROCESSORS_REGISTRY["http"]
        processor3 = sut.PROCESSORS_REGISTRY["ftp"]
        processor1.acquire = mocker.MagicMock()
        processor2.acquire = mocker.MagicMock()
        processor3.acquire = mocker.MagicMock()

        mocker.patch("src.exchange.aiofiles.os.path.isfile", side_effect=[True])
        filename = f"{str(config.source).removesuffix('/')}/filename.mp4"
        changes = {(Change.added, filename)}

        mock_awatch(changes)
        async with sut:
            await asyncio.sleep(0.1)
            processor1.acquire.assert_called_once()
            message = processor1.acquire.call_args.args[0]
            assert message.body.get("filename") == filename
            processor2.acquire.assert_not_called()
            processor3.acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_crash_when_no_webapp(self, config):
        async with FileWatcher(config=config, with_webapp=False):
            ...

    @pytest.mark.asyncio
    async def test_should_not_initialize_notifiers_when_no_webapp(self, config):
        sut = FileWatcher(config)
        async with sut:
            for p in sut.PROCESSORS_REGISTRY.values():
                assert p.notifier is None

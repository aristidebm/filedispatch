import uuid
from pathlib import Path

from watchfiles import Change

import pytest
from src.watchers import FileWatcher

pytestmark = pytest.mark.watcher


@pytest.fixture(autouse=True)
def mock_processors(mocker):
    # Mock background tasks (since their running forever and we are going to wait them manually)

    # spec=True, cause a check is done in library to make sure they are dealing with a ServiceTask
    mocker.patch("src.processors.LocalStorageProcessor._process", spec=True)
    mocker.patch("src.processors.HttpStorageProcessor._process", spec=True)
    mocker.patch("src.processors.FtpStorageProcessor._process", spec=True)
    mocker.patch("src.notifiers.Notifier._notify", spec=True)
    mocker.patch("aiofiles.os.path.isfile", returned_value=True)


@pytest.fixture
def mock_isfile(mocker):
    def _inner_fun(**kwargs):
        mocker.patch("aiofiles.os.path.isfile", **kwargs)

    return _inner_fun


class TestWatch:
    @pytest.fixture(autouse=True)
    def mock_provide(self, mocker):
        mocker.patch("src.watchers.FileWatcher._provide", spec=True)

    @pytest.mark.asyncio
    async def test_new_files_are_queued(
        self, mocker, config, filesystem, await_scheduled_task, mock_isfile, mock_awatch
    ):
        mock_put = mocker.patch("src.watchers.Queue.put")

        dir_ = Path(filesystem.name) / "mnt"
        filename = dir_ / f"tmp-{uuid.uuid4()}.mp4"

        mock_isfile(returned_value=True)

        # new change occurs in the watching directory.
        changes = {(Change.added, filename)}
        mock_awatch(changes)
        async with FileWatcher(config=config) as watcher:
            assert watcher.unprocessed.empty()
            await await_scheduled_task()
            # https://docs.python.org/3/library/unittest.mock.html#any
            mock_put.assert_awaited_once_with((filename, mocker.ANY))

    @pytest.mark.asyncio
    async def test_existing_files_are_queued(
        self, mocker, config, filesystem, await_scheduled_task, mock_awatch, mock_isfile
    ):
        queue_put = mocker.patch("src.watchers.Queue.put")

        dir_ = Path(filesystem.name) / "mnt"
        filename = dir_ / f"tmp-{uuid.uuid4()}.mp4"

        mock_isfile(returned_value=True)

        # no change occurs in the watching directory.
        changes = set()
        mock_awatch(changes)

        # Existing file in watching directory
        mocker.patch("src.watchers.Path.glob", return_value=[filename])

        async with FileWatcher(config=config):
            await await_scheduled_task()
            # Make sure the file is added to the processing queue
            queue_put.assert_awaited_once_with((filename, mocker.ANY))

    @pytest.mark.asyncio
    async def test_ignore_new_directories_and_symlinks(
        self, mocker, config, filesystem, await_scheduled_task, mock_isfile, mock_awatch
    ):

        queue_put = mocker.patch("src.watchers.Queue.put")

        dir_ = Path(filesystem.name) / "mnt"
        filename = dir_ / f"tmp-{uuid.uuid4()}"  # is not a file

        mock_isfile(returned_value=False)

        # new change occurs in the watching directory.
        changes = {(Change.added, filename)}
        mock_awatch(changes)

        async with FileWatcher(config=config) as watcher:

            assert watcher.unprocessed.empty()
            await await_scheduled_task()
            # Make sure the file is added to the processing queue
            queue_put.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ignore_source_subdirectories_changes(
        self, mocker, config, filesystem, await_scheduled_task, mock_isfile, mock_awatch
    ):

        queue_put = mocker.patch("src.watchers.Queue.put")

        dir_ = Path(filesystem.name) / "mnt"
        filename = (
            dir_ / "video" / f"tmp-{uuid.uuid4()}.mp4"
        )  # change in a subdirectory

        mock_isfile(returned_value=True)

        # new change occurs in the watching directory.
        changes = {(Change.added, filename)}
        mock_awatch(changes)

        async with FileWatcher(config=config) as watcher:
            assert watcher.unprocessed.empty()
            # Make sure the file is added to the processing queue
            queue_put.assert_not_awaited()


class TestProvid:
    @pytest.fixture(autouse=True)
    def mock_provide(self, mocker):
        mocker.patch("src.watchers.FileWatcher._watch", spec=True)

    @pytest.mark.asyncio
    async def test_changes_are_sent_to_processor(
        self, config, mocker, await_scheduled_task
    ):
        # mocks

        source = Path("/parent") / "mnt"

        destination = source / "video"
        filename = source / f"tmp-{uuid.uuid4()}.mp4"  # change in a subdirectory

        mocker.patch(
            "src.watchers.Queue.get",
            side_effect=[(filename, destination), Exception],
        )
        mocker.patch("src.watchers.FileWatcher.sleep")  # don't want to really sleep

        # mock the processor
        mock = mocker.Mock()
        base_mock = mocker.Mock(return_value=mock)
        mock.acquire = mocker.Mock(return_value=None)
        mock.maybe_start = mocker.AsyncMock()

        mocker.patch("src.watchers.FileWatcher._get_processor", new=base_mock)

        async with FileWatcher(config) as watcher:
            assert watcher.unprocessed.empty()
            await await_scheduled_task()
            mock.acquire.assert_called_once_with(filename, destination)

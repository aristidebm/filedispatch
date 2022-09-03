"""
https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
"""
import asyncio
import os
import tempfile
from typing import Set, Tuple

import pytest
from watchfiles import Change

from src.cli import Config


@pytest.fixture
def config(configfile, filesystem):
    conf = Config(config=configfile.name)()
    yield conf


@pytest.fixture
def configfile():
    data = """source: mnt/
folders:
  - path: mnt/video
    extensions: [mp4, flv, avi, mov, wmv, webm, mkv]
  - path: http://localhost:8000/documents/audio
    extensions: [mp3, wav, ogg]
  - path: ftp://username:password@127.0.0.1/home/user/documents
    extensions: [pdf, djvu, tex, ps, doc, docx, ppt, pptx, xlsx, odt, epub]
  - path: file:///tmp/image
    extensions: [png, jpg, jpeg, gif, svg]
    """
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".yml")
    config.write(data)
    config.flush()  # Very important, without this file will seems to be empty
    # https://docs.pytest.org/en/6.2.x/fixture.html#teardown-cleanup-aka-fixture-finalization
    yield config
    config.close()


@pytest.fixture
def filesystem():  # FIXME: It can be handy to rely on pytest tmp_path fixture
    tempdir = tempfile.TemporaryDirectory()
    os.mkdir(os.path.join(tempdir.name, "mnt"))
    os.mkdir(os.path.join(tempdir.name, "mnt/video"))
    os.mkdir(os.path.join(tempdir.name, "mnt/audio"))
    os.mkdir(os.path.join(tempdir.name, "mnt/document"))
    os.mkdir(os.path.join(tempdir.name, "mnt/image"))
    os.chdir(tempdir.name)
    # https://docs.pytest.org/en/6.2.x/fixture.html#teardown-cleanup-aka-fixture-finalization
    yield tempdir
    tempdir.cleanup()


# @pytest.fixture
# def new_file():
#
#     _files = []  # keep track of resources
#
#     # Delegates file creation to test method, this is nice workaround for passing data to fixture by using markers.
#     def create(dir, *, suffix: str = None, binary=True):
#         if not suffix:
#             d = tempfile.TemporaryDirectory(dir=dir)
#             _files.append(d)
#             return d
#
#         mode = f"w+{'b' if binary else 't'}"
#         suffix = suffix.removeprefix(".")
#         # In some tests we need to be able to re-open the file for some kind of processing, using NamedTemporaryFile,
#         # this is only achievable on Unix based system, not on windows (https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile).
#         # so we will use open.
#         path = os.path.join(dir, "".join([f"tmp-{uuid.uuid4()}", f".{suffix}"]))
#
#         with open(path, mode) as f:
#             _files.append(f.name)
#             f.flush()
#
#         # return name not f.name for the function to have a uniform interface.
#         return f
#
#     def cleanup():
#         # NamedTemporaryFiles automatically close themselves as state here.
#         # https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile
#         for f in _files:
#             if isinstance(f, tempfile.TemporaryDirectory):
#                 f.cleanup()
#             elif isinstance(f, str):
#                 try:
#                     os.unlink(f)
#                 except OSError:
#                     ...
#
#     yield create
#
#     cleanup()


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# FIXME: we don't necessarily want to mock server when testing the server itself.
@pytest.fixture(autouse=True)
def mock_server(request, mocker):
    if "server" in request.keywords:
        return
    # Mock the server to the prevent actual server launching when running tests
    return mocker.patch("src.api.server.WebServer.run_app")


@pytest.fixture
def await_scheduled_task():
    async def _await(return_exceptions=True):
        ret_tasks = [
            t
            for t in asyncio.all_tasks()
            if t is not asyncio.current_task()  # Except the test function itself
        ]

        # Explicitly await tasks scheduled by `asyncio.create_task`
        await asyncio.gather(
            *ret_tasks,
            return_exceptions=return_exceptions,  # return_exception suppress cancellation errors
        )

    return _await


@pytest.fixture
def mock_awatch(mocker):
    mock_awatch = mocker.patch("src.watchers.awatch")
    _changes: Set[Tuple[Change, str]] = set()  # changes must be set

    async def _mock(conf):
        yield _changes

    # mock awatch to avoid the infinite define inside it.
    mock_awatch.side_effect = _mock

    def _get_changes(changes: Set[Tuple[Change, str]]):
        _changes.update(changes)

    yield _get_changes
    # clear all changes
    _changes.clear()

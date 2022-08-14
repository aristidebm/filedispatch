"""
https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
"""
import asyncio
import os
import tempfile
import pytest
import pytest_asyncio

from src.cli import Config

# https://stackoverflow.com/questions/66054356/multiple-async-unit-tests-fail-but-running-them-one-by-one-will-passa


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
  - path: http://localhost/documents/audio
    extensions: [mp3, wav, ogg]
  - path: ftp://username:password@localhost/home/user/documents
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
def filesystem():
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


# Using level event loop on function scope make the test suite fail, but when run one by one everyting work as expected,
# so we will use the same loop for an entire session [source](https://github.com/pytest-dev/pytest-asyncio#event_loop)
@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

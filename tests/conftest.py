"""
https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
"""
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
import pytest


@pytest.fixture
def configfile():
    data = """root: mnt/
folders:
  - label: videos
    path: mnt/video
    extensions: [mp4, flv, avi, mov, wmv, webm, mkv]
  - label: audios
    path: mnt/audio
    extensions: [mp3, wav, ogg]
  - label: documents
    path: mnt/document 
    extensions: [pdf, djvu, tex, ps, doc, docx, ppt, pptx, xlsx, odt, epub]
  - label: images
    path: mnt/image
    extensions: [png, jpg, jpeg, gif, svg]
    """
    config = NamedTemporaryFile(mode="w+", suffix=".yml")
    config.write(data)
    config.flush()  # Veru important, without this file will seems to be empty
    # https://docs.pytest.org/en/6.2.x/fixture.html#teardown-cleanup-aka-fixture-finalization
    yield config


@pytest.fixture
def filesystem():
    tempdir = TemporaryDirectory()
    os.mkdir(os.path.join(tempdir.name, "mnt"))
    os.mkdir(os.path.join(tempdir.name, "mnt/video"))
    os.mkdir(os.path.join(tempdir.name, "mnt/audio"))
    os.mkdir(os.path.join(tempdir.name, "mnt/document"))
    os.mkdir(os.path.join(tempdir.name, "mnt/image"))
    os.chdir(tempdir.name)
    # https://docs.pytest.org/en/6.2.x/fixture.html#teardown-cleanup-aka-fixture-finalization
    yield tempdir

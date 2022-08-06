from tempfile import NamedTemporaryFile

import pytest
from src.config import Config


@pytest.fixture
def bad_configfile():
    data = """source: mnt/
folders:
  - label: videos
    path: mnt/video
    extensions: [mp4, flv, avi, mov, wmv, webm, mkv]
  - label: audios # missing path
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


def test_config_generation_success(mocker, configfile, filesystem):
    mock = mocker.patch("src.config.logger.debug")
    conf = Config(config=configfile.name)()
    assert conf is not None
    mock.assert_not_called()


def test_config_generation_failure(mocker, bad_configfile, filesystem):
    debug = mocker.patch("src.config.logger.debug")
    error = mocker.patch("src.config.logger.error")
    conf = Config(config=bad_configfile.name)()
    assert conf is None
    debug.assert_called_once()
    error.assert_called_once()

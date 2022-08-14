from tempfile import NamedTemporaryFile

import pytest
import pytest_asyncio
from src.config import Config


pytestmark = pytest.mark.config


@pytest_asyncio.fixture
def bad_configfile():
    data = """source: mnt/
folders:
  - path: mnt/video
    extensions: [mp4, flv, avi, mov, wmv, webm, mkv]
  - path: http://localhost/documents/audio
  - path: ftp://username:password@localhost/home/user/documents
    extensions: [pdf, djvu, tex, ps, doc, docx, ppt, pptx, xlsx, odt, epub]
  - path: file:///tmp/image
    extensions: [png, jpg, jpeg, gif, svg]
        """

    config = NamedTemporaryFile(mode="w+", suffix=".yml")
    config.write(data)
    config.flush()  # Veru important, without this file will seems to be empty
    # https://docs.pytest.org/en/6.2.x/fixture.html#teardown-cleanup-aka-fixture-finalization
    yield config


@pytest.mark.config
def test_config_generation_success(mocker, configfile, filesystem):
    mock = mocker.patch("src.config.logger.debug")
    conf = Config(config=configfile.name)()
    assert conf is not None
    mock.assert_not_called()


@pytest.mark.config
def test_config_generation_failure(mocker, bad_configfile, filesystem):
    debug = mocker.patch("src.config.logger.debug")
    error = mocker.patch("src.config.logger.error")
    conf = Config(config=bad_configfile.name)()
    assert conf is None
    debug.assert_called_once()
    error.assert_called_once()

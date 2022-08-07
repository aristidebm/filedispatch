import argparse
import os.path
import logging

from .config import Config
from .core import FileDispatch

logger = logging.getLogger(__name__)


def run():
    args = add_argumenent()
    config = args.config.name
    args.config.close()

    if not check_file_format(config):
        # FIXME: Log something here.
        return

    config = Config(config)()

    if not config:
        logger.error("The config file is malformed")
        return

    dispatcher = FileDispatch(config)
    dispatcher.run()


def add_argumenent():
    parser = argparse.ArgumentParser(description="Dispatch new added file in a folder")
    parser.add_argument("-l", "--log-level", help="logging level")
    parser.add_argument("config", help="config path", type=argparse.FileType())
    args = parser.parse_args()
    return args


def check_file_format(filename, format=None):
    format = format or ["yml", "yaml"]
    _, ext = os.path.splitext(filename)
    ext = ext.removeprefix(".")
    return ext in format

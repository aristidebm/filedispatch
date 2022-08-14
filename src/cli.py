import argparse
import os.path
import logging
import sys

from .config import Config
from .watchers import FileWatcher

logger = logging.getLogger(__name__)


def main():
    args = add_argumenent()
    config = args.config.name
    args.config.close()

    if not check_file_format(config):
        logger.error(
            "The config file has wrong extension. Did you provide (.yaml/.yml) file ?"
        )
        return

    config = Config(config)()

    if not config:
        logger.error("The config file is malformed")
        return

    dispatcher = FileWatcher(config)
    dispatcher.run()


# source: https://stackoverflow.com/a/4042861/13837279
class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage()
        sys.exit(2)


def add_argumenent():
    parser = CustomArgumentParser(description="Dispatch new added file in a folder")
    parser.add_argument("-l", "--log-level", help="logging level")
    parser.add_argument("config", help="config file path", type=argparse.FileType())
    args = parser.parse_args()
    return args


def check_file_format(filename, format=None):
    format = format or ["yml", "yaml"]
    _, ext = os.path.splitext(filename)
    ext = ext.removeprefix(".")
    return ext in format

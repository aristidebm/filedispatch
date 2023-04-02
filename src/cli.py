"""
filedispath is a simple, configurable, async based and user-friendly cli app for automatic file organization.
It listens to a configured source folder for new files and copy or move them to the appropriate destination according to the configuration file.
"""

from __future__ import annotations
import argparse
import functools
import os.path
import logging
import pathlib
import enum
import traceback
import sys
import socket as sock
from datetime import datetime

import pydantic
from pydantic import HttpUrl, FilePath
from pydantic import (
    BaseModel,
    Field,
    validator,
    root_validator,
    ValidationError,
    parse_obj_as,
)
from pydantic_cli import run_and_exit, to_runner, _get_error_exit_code  # noqa
from daemons import daemonizer

from . import __version__
from .config import Config, parse_logger_config
from .exchange import FileWatcher
from .utils import BASE_DIR, isfile, has_permission

logger = logging.getLogger(__name__)


class ExceptionHandler:
    def __call__(self, ex, *args, **kwargs):
        if isinstance(ex, pydantic.ValidationError):
            ex = ex.errors()[0]["msg"]
        sys.stderr.write(str(ex))
        # exc_type, exc_value, exc_traceback = sys.exc_info()
        # traceback.print_tb(exc_traceback, file=sys.stderr)
        return _get_error_exit_code(ex, 1)


def setup_logger(args):
    logger_config = parse_logger_config(BASE_DIR / "logging-config.yaml")

    if logger_config and args.pidfile and args.log_file:
        logger_config["loggers"][""]["handlers"].append("file")
        logger_config["handlers"]["file"]["filename"] = str(args.log_file)

    if logger_config and args.log_level:
        for h in logger_config.get("handlers", []):
            logger_config["handlers"][h]["level"] = str(args.log_level)

        for s in logger_config.get("loggers", []):
            logger_config["loggers"][s]["level"] = str(args.log_level)

    logging.config.dictConfig(logger_config)


class LogLevel(str, enum.Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Arguments(BaseModel):
    with_webapp: bool = Field(
        False,
        description="Launch the embedded web app",
        cli=("--with-webapp",),
    )
    move: bool = Field(
        False,
        description="Move files",
        cli=("-m", "--move"),
    )
    exit: bool = Field(
        False,
        description="Exit the app",
        cli=("-x", "--exit"),
    )
    log_level: LogLevel = Field(
        LogLevel.INFO,
        description="Set the log level",
        cli=("--log-level",),
    )
    db: pathlib.Path | None = Field(
        None,
        description="database file path",
        cli=("--db",),
    )
    log_file: pathlib.Path | None = Field(
        None,
        description="log file path",
        cli=("--log-file",),
    )
    pid_file: pathlib.Path | None = Field(
        None,
        description="pid file path",
        cli=("-p", "--pid-file"),
    )
    server_url: HttpUrl | None = Field(
        None,
        description="webapp host url",
        cli=("--server-url",),
    )
    endpoint: pathlib.Path | None = Field(
        "api/v1/logs",
        description="webapp endpoint to post log to.",
        cli=("--endpoint",),
    )
    config: FilePath = Field(
        ...,
        description="config file path",
        cli=("-c", "--config"),
    )

    @validator("config")
    def validate_config_file(cls, value):
        if value:
            value = value.resolve()
            allowed_ext = ["yml", "yaml"]
            _, ext = os.path.splitext(value)
            ext = ext.removeprefix(".")

            if ext not in allowed_ext:
                raise ValueError(
                    "The config file has wrong extension. Did you provide (.yaml/.yml) file ?"
                )
            if not has_permission(value, mode=os.R_OK):
                raise ValueError(f"The config file [{value}] is not readable.")
        return value

    @root_validator()
    def validate_arguments(cls, values):
        server_url = values.get("server_url")
        with_webapp = values.get("with_webapp")
        exit = values.get("exit")
        pid_file = values.get("pid_file")

        if with_webapp and not server_url:
            server_url = parse_obj_as(HttpUrl, "http://127.0.0.1:3001")
            values["server_url"] = server_url

        if with_webapp and server_url:
            if cls._is_open(server_url):
                raise ValueError(
                    f"The port {server_url.port} is already in used. Please change the port and retry."
                )

        if with_webapp and not values.get("db"):
            raise ValueError("The database file is required to start the local webapp.")

        if exit and not pid_file:
            raise ValueError("The pidfile is requiered to exit the daemon.")

        if pid_file:
            cls._validate_file(pid_file)

        if pid_file and not values.get("log_file"):
            log_file = pid_file.parent / "filedipatch.log"
            cls._validate_file(log_file)

        if not pid_file and values.get("log_file"):
            values["log_file"] = None

        return values

    @classmethod
    def _validate_file(cls, filename):
        if filename:
            filename = filename.resolve()
            if not os.path.exists(filename):
                try:
                    if has_permission(filename.parent, os.W_OK):
                        filename.touch()
                    else:
                        raise OSError
                except OSError:
                    raise ValueError(
                        f"Does not have right permissions to create {filename}. Please set these permission(s) and retry."
                    )

            if isfile(filename) and (
                not has_permission(filename, os.W_OK)
                or not has_permission(filename, os.R_OK)
            ):
                raise ValueError(
                    f"Does not have right permissions on {filename}. Please set these permission(s) and retry."
                )
        return filename

    @classmethod
    def _is_open(cls, url: HttpUrl):
        s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        try:
            address = (url.host, int(url.port))
        except TypeError as exp:
            raise ValueError(exp)
        res = s.connect_ex(address)
        return not res


def run(args: Arguments):
    config = Config(args.config)()

    dispatcher = FileWatcher(
        config,
        server_url=args.server_url and str(args.server_url),
        endpoint=args.endpoint and str(args.endpoint),
        log_file=args.log_file,
        db=args.db,
        log_level=args.log_level,
        with_webapp=args.with_webapp,
        delete=args.move,
    )

    if args.pid_file or args.exit:
        demonic = daemonizer.run(pidfile=str(args.pid_file))(dispatcher.run)
        if args.exit:
            demonic.stop()
            sys.exit(0)
        demonic()
    else:
        dispatcher.run()


def main():
    run_and_exit(
        Arguments,
        run,
        version=f"%(prog)s {__version__} (https://github.com/aristidebm/filedispatch)",
        description=__doc__,
        exception_handler=ExceptionHandler(),
        prologue_handler=setup_logger,
    )


# if __name__ == "__main__":
#     run_and_exit(
#         Arguments,
#         main,
#         version=f"%(prog)s {__version__} (https://github.com/aristidebm/filedispatch)",
#         description="",
#         exception_handler=...,
#     )

# def main():
#     args, parser = parse_argv(sys.argv[1:])
#     config = Config(args.config)()
#
#     def get_log_file():
#         return args.log_file if args.daemon else None
#
#     def get_server_url():
#         if args.server_url:
#             return args.server_url
#
#         if args.with_webapp and not args.server_url:
#             return "http"
#
#     if not config:
#         logger.error(f"The configuration file [{args.config}] is incorrectly formatted")
#         return
#
#     if args.daemon and not args.pidfile:
#         parser.error("Cannot run the daemon. Have you forgotten to provide a pidfile ?")
#
#     if args.exit and not args.pidfile:
#         parser.error(
#             "Cannot exit the daemon. Have you forgotten to provide a pidfile ?"
#         )
#
#     if args.daemon and args.exit:
#         parser.error("You cannot provide both --daemon and --exit")
#
#     if args.pidfile and (args.daemon or args.exit):
#         pidfile = pathlib.Path(args.pidfile).resolve()
#         if pidfile.exists() and not has_permission(pidfile, mode=os.W_OK):
#             parser.error(f"The pidfile [{pidfile}] is not writable.")
#
#     if args.with_webapp and not args.db:
#         parser.error("The db is required to launch the webapp")
#
#     # FIXME: remove the compling below, user may provide the db
#     #  without the need to serve it's data.
#     if not args.with_webapp and args.db:
#         parser.error("The db is forbid when no webapp")
#
#     dispatcher = FileWatcher(
#         config,
#         host=args.host,
#         port=args.port,
#         log_file=get_log_file(),
#         db=args.db,
#         log_level=args.log_level,
#         with_webapp=args.with_webapp,
#         delete=args.move,
#     )
#
#     setup_logging(args)
#
#     if args.daemon or args.exit:
#         demonic = daemonizer.run(pidfile=pidfile)(dispatcher.run)
#         if args.exit:
#             demonic.stop()
#             sys.exit(0)
#         demonic()
#     else:
#         dispatcher.run()
# argparse.ArgumentParser

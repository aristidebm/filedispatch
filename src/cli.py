import argparse
import functools
import os.path
import logging
import pathlib
import sys
from datetime import datetime

from daemons import daemonizer

from . import __version__
from .config import Config
from .watchers import FileWatcher
from .utils import BASE_DIR, isfile, has_permission

logger = logging.getLogger(__name__)


def validate_config(filename):
    allowed_ext = ["yml", "yaml"]
    _, ext = os.path.splitext(filename)
    ext = ext.removeprefix(".")

    if ext not in allowed_ext:
        raise argparse.ArgumentTypeError(
            "The config file has wrong extension. Did you provide (.yaml/.yml) file ?"
        )
    if not isfile(filename) or not has_permission(filename, mode=os.R_OK):
        raise argparse.ArgumentError(
            f"The config file [{filename}] doesn't exists or is not readable."
        )
    return pathlib.Path(filename)


validate_config.__name__ = "ConfigFile"


def validate_log_file(filename):
    if filename and (
        not isfile(filename) or not has_permission(filename, mode=os.R_OK)
    ):
        raise argparse.ArgumentError(
            f"The config file [{filename}] doesn't exists or is not readable."
        )
    return filename


validate_log_file.__name__ = "LogFile"


# Inspired by https://github.com/msztolcman/sendria/blob/master/sendria/cli.py


def parse_argv(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="filedispatch")
    version = f"%(prog)s {__version__} (github link to filedispatch)"
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=version,
        help="Display the version and exit",
    )
    parser.add_argument(
        "-H", "--host", metavar="IP", help="web app host ip (default: 127.0.0.1)"
    )
    parser.add_argument(
        "-P", "--port", type=int, metavar="PORT", help="web app port (default: 3001)"
    )
    parser.add_argument(
        "-d", "--daemon", help="Run as daemon", action="store_true", default=False
    )
    parser.add_argument(
        "-x", "--exit", action="store_true", help="Sends SIGTERM to the running daemon"
    )
    parser.add_argument(
        "--no-web-app",
        help="Whether to launch web app",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--log-file",
        type=validate_log_file,
        help="Where logs have to come if working in daemon. Ignored if working in foreground.",
    )
    parser.add_argument(
        "--log-level",
        help="Logging level (default: INFO)",
    )

    parser.add_argument("-p", "--pidfile", help="PID storage path")

    parser.add_argument(
        "-c",
        "--config",
        metavar="CONFIG",
        type=validate_config,
        required=True,
        help="configuration file to use",
    )
    return parser.parse_args(argv), parser


def main():
    args, parser = parse_argv(sys.argv[1:])
    config = Config(args.config)()
    pidfile = None

    if not config:
        logger.error(f"The configuration file [{args.config}] is incorrectly formatted")
        return

    if args.daemon and not args.log_file:
        args.log_file = pathlib.Path.cwd() / "filedispatch.log"

    if args.daemon or args.exit:
        if not args.pidfile:
            parser.error(
                "Can't run/exit the daemon. Have you forgotten to provide a pidfile ?"
            )

        pidfile = pathlib.Path(args.pidfile)
        if not pidfile.is_absolute():
            pidfile = pidfile.cwd() / pidfile

        if pidfile.exists() and not has_permission(pidfile, mode=os.W_OK):
            parser.error(f"The pidfile [{pidfile}] is not writable.")

        if not pidfile.exists() and not has_permission(pidfile.parent, mode=os.W_OK):
            parser.error(f"The pidfile [{pidfile}] is not writable.")

        if args.daemon and args.exit:
            parser.error("You can't provide --daemon and --exit")

    dispatcher = FileWatcher(
        config,
        host=args.host,
        port=args.port,
        log_file=args.log_file,
        log_level=args.log_level,
        no_web_app=args.no_web_app,
    )

    if args.daemon or args.exit:
        demonic = daemonizer.run(pidfile=pidfile)(dispatcher.run)
        if args.exit:
            demonic.stop()
            sys.exit(0)
        demonic()
    else:
        dispatcher.run()

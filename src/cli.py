import argparse
import functools
import os.path
import logging
import pathlib
import sys
from datetime import datetime

from daemons import daemonizer

from . import __version__
from .config import Config, parse_logging_config
from .exchange import FileWatcher
from .utils import BASE_DIR, isfile, has_permission

logger = logging.getLogger(__name__)


def name(name):
    def wrapper(f):
        def wrappee(*args, **kwargs):
            return f(*args, **kwargs)

        wrappee.__name__ = name
        return wrappee

    return wrapper


@name("CONFIGFILE")
def validate_config(filename):
    if filename:
        filename = pathlib.Path(filename).resolve()

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
    return str(filename)


@name("LOGFILE")
def validate_log_file(filename):
    return _validate_file(filename)


@name("DBFILE")
def validate_db_file(filename):
    return _validate_file(filename)


@name("PIDFILE")
def validate_pid_file(filename):
    return _validate_file(filename)


def _validate_file(filename):
    if filename:
        filename = pathlib.Path(filename).resolve()

        if not os.path.exists(filename):
            try:
                if has_permission(filename.parent, os.W_OK):
                    filename.touch()
                else:
                    raise OSError
            except OSError:
                raise argparse.ArgumentError(
                    f"Does not have right permissions to create {filename}. Please set these permission(s) and retry."
                )

        if isfile(filename) and (
            not has_permission(filename, os.W_OK)
            or not has_permission(filename, os.R_OK)
        ):
            raise argparse.ArgumentError(
                f"Does not have right permissions on {filename}. Please set these permission(s) and retry."
            )

    return str(filename)


def parse_argv(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="filedispatch")
    version = f"%(prog)s {__version__} (https://github.com/aristidebm/filedispatch)"
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=version,
        help="Display the version and exit",
    )
    parser.add_argument(
        "-H",
        "--host",
        metavar="IP",
        help="web app host ip (default: 127.0.0.1)",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        metavar="PORT",
        help="web app port (default: 3001)",
    )
    parser.add_argument(
        "-d",
        "--daemon",
        help="Run as daemon",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-x",
        "--exit",
        action="store_true",
        help="Sends SIGTERM to the running daemon (needs --pidfile)",
    )
    parser.add_argument(
        "--with-webapp",
        help="Whether to launch the local web app (default: false, needs --db when true)",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-m",
        "--move",
        help="Whether to move files from source (default: false)",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--log-level",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        metavar="LOGFILE",
        type=validate_log_file,
        help="Where logs have to come if working in daemon. Ignored if working in foreground ($HOME/log-file if the db file is relative)",
    )
    parser.add_argument(
        "-p",
        "--pidfile",
        metavar="PIDFILE",
        type=validate_pid_file,
        help="Use as PID file ($HOME/pid-file if the pid file is relative)",
    )
    parser.add_argument(
        "--db",
        metavar="DBFILE",
        type=validate_db_file,
        help="Use as DB file ($HOME/db-file if the db file is relative)",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="CONFIG",
        type=validate_config,
        required=True,
        help="configuration file to use",
    )
    return parser.parse_args(argv), parser


def setup_logging(args):
    logging_config = parse_logging_config(BASE_DIR / "logging-config.yaml")
    if logging_config and args.log_file and args.daemon:
        logging_config["loggers"][""]["handlers"].append("file")
        logging_config["handlers"]["file"]["filename"] = args.log_file

    if logging_config and (not args.log_file or (args.log_file and not args.daemon)):
        logging_config["handlers"].pop("file", None)

    if logging_config and args.log_level and args.daemon:
        for h in logging_config.get("handlers", []):
            logging_config["handlers"][h]["level"] = args.log_level

        for s in logging_config.get("loggers", []):
            logging_config["loggers"][s]["level"] = args.log_level

    logging.config.dictConfig(logging_config)


def main():
    args, parser = parse_argv(sys.argv[1:])
    config = Config(args.config)()

    def get_log_file():
        return args.log_file if args.daemon else None

    if not config:
        logger.error(f"The configuration file [{args.config}] is incorrectly formatted")
        return

    if args.daemon and not args.pidfile:
        parser.error("Cannot run the daemon. Have you forgotten to provide a pidfile ?")

    if args.exit and not args.pidfile:
        parser.error(
            "Cannot exit the daemon. Have you forgotten to provide a pidfile ?"
        )

    if args.daemon and args.exit:
        parser.error("You cannot provide both --daemon and --exit")

    if args.pidfile and (args.daemon or args.exit):
        pidfile = pathlib.Path(args.pidfile).resolve()
        if pidfile.exists() and not has_permission(pidfile, mode=os.W_OK):
            parser.error(f"The pidfile [{pidfile}] is not writable.")

    if args.with_webapp and not args.db:
        parser.error("The db is required to launch the webapp")

    # FIXME: remove the compling below, user may provide the db
    #  without the need to serve it's data.
    if not args.with_webapp and args.db:
        parser.error("The db is forbid when no webapp")

    dispatcher = FileWatcher(
        config,
        host=args.host,
        port=args.port,
        log_file=get_log_file(),
        db=args.db,
        log_level=args.log_level,
        with_webapp=args.with_webapp,
        delete=args.move,
    )

    setup_logging(args)

    if args.daemon or args.exit:
        demonic = daemonizer.run(pidfile=pidfile)(dispatcher.run)
        if args.exit:
            demonic.stop()
            sys.exit(0)
        demonic()
    else:
        dispatcher.run()

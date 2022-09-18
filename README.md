# File Dispatch

File dispatch is an [asyncio](https://docs.python.org/3.9/library/asyncio.html) based directory watcher that 
basically watch a directory for some configured file extension and send the received file
to some configured destination.

## Project structure

## Usage

### Monitor running services [source](https://pypi.org/project/aiomonitor-ng/)
connect to aiomonitor telnet server by using `nc` utility or other telnet client.
```shell
nc 127.0.0.1 50101
```

### filedispatch cli
```shell
usage: filedispatch [-h] [-v] [-H IP] [-P PORT] [-d] [-x] [--no-web-app] [--log-file LOG_FILE] [--log-level LOG_LEVEL] [-p PIDFILE] -c CONFIG

options:
  -h, --help            show this help message and exit
  -v, --version         Display the version and exit
  -H IP, --host IP      web app host ip (default: 127.0.0.1)
  -P PORT, --port PORT  web app port (default: 3001)
  -d, --daemon          Run as daemon
  -x, --exit            Sends SIGTERM to the running daemon
  --no-web-app          Whether to launch web app
  --log-file LOG_FILE   Where logs have to come if working in daemon. Ignored if working in foreground.
  --log-level LOG_LEVEL
                        Logging level (default: INFO)
  -p PIDFILE, --pidfile PIDFILE
                        PID storage path
  -c CONFIG, --config CONFIG
                        configuration file to use
```

## Features

+ Support Local file moving
+ Support Http chunck binary stream file upload
+ Support Ftp file upload 
+ Expose a monitoring web api
+ Well tested project
+ ...

## Main dependencies

+ [pydantic](https://pypi.org/project/pydantic/)
+ [mode](https://pypi.org/project/mode-ng/)
+ [watchfiles](https://pypi.org/project/watchfiles/)
+ [aiohttp](https://docs.aiohttp.org/en/stable/)
+ [aioftp](https://pypi.org/project/aioftp/)
+ [aiofiles](https://pypi.org/project/aiofiles/)
+ [pipyka](https://pypi.org/project/PyPika/)
+ [aiosqlite](https://pypi.org/project/aiosqlite3/)
+ [daemons](https://pypi.org/project/daemons/)

## Tests

## Known Issues

## Licence

# File Dispatch

File dispatch is an [asyncio](https://docs.python.org/3.9/library/asyncio.html) based directory watcher that 
basically watch a directory for some configured file extension and send the received file
to some configured destination.

## Project structure
```
.
├── docs
│   ├── filedispatch-architecute.png
│   ├── api
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── queries.py
│   │   ├── server.py
│   │   └── views.py
│   ├── cli.py
│   ├── config.py
│   ├── __init__.py
│   ├── notifiers.py
│   ├── processors.py
│   ├── schema.py
│   ├── utils.py
│   └── watchers.py
├── tests
│   ├── api
│   │   ├── __init__.py
│   │   └── test_log_api.py
│   ├── base.py
│   ├── conftest.py
│   ├── factories.py
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_notifiers.py
│   ├── test_processors.py
│   ├── test_utils.py
│   └── test_watchers.py
├── CHANGELOG.md
├── config.example.yml
├── CONTRIBUTE.md
├── db.sqlite3
├── LICENCE
├── Makefile
├── poetry.lock
├── pyproject.toml
├── pytest.ini
├── README.md
├── run.py
├── setup.py
```

## Usage

### Monitor running services [source](https://pypi.org/project/aiomonitor-ng/)
connect to aiomonitor telnet server by using `nc` utility or other telnet client.
```shell
nc 127.0.0.1 50101
```

### filedispatch cli
```shell
usage: filedispatch [-h] [-v] [-H IP] [-P PORT] [-d] [-x] [--no-webapp] [--log-file LOG_FILE] [--log-level LOG_LEVEL] [-p PIDFILE] -c CONFIG

options:
  -h, --help            show this help message and exit
  -v, --version         Display the version and exit
  -H IP, --host IP      web app host ip (default: 127.0.0.1)
  -P PORT, --port PORT  web app port (default: 3001)
  -d, --daemon          Run as daemon
  -x, --exit            Sends SIGTERM to the running daemon
  --no-webapp           Whether to launch web app
  --log-file LOG_FILE   Where logs have to come if working in daemon. Ignored if working in foreground.
  --log-level LOG_LEVEL
                        Logging level (default: INFO)
  -p PIDFILE, --pidfile PIDFILE
                        PID storage path
  -c CONFIG, --config CONFIG
                        configuration file to use
```

### Config file example
```yaml

source: /home/filedispatch/downloads
folders:
  - path: ftp://username:password@ftp.foo.org/home/user/videos
    extensions: [mp4, flv, avi, mov, wmv, webm, mkv]
  - path: https://server/documents/audios
    extensions: [mp3, wav, ogg]
    fieldname: document
  - path: file:///tmp/documents/ebooks
    extensions: [pdf, djvu, tex, ps, doc, docx, ppt, pptx, xlsx, odt, epub]
  - path: /tmp/documents/images
    extensions: [png, jpg, jpeg, gif, svg]
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
+ [mode-streaming](https://pypi.org/project/mode-streaming/)
+ [watchfiles](https://pypi.org/project/watchfiles/)
+ [aiohttp](https://docs.aiohttp.org/en/stable/)
+ [aioftp](https://pypi.org/project/aioftp/)
+ [aiofiles](https://pypi.org/project/aiofiles/)
+ [pypika](https://pypi.org/project/PyPika/)
+ [aiosqlite](https://pypi.org/project/aiosqlite3/)
+ [daemons](https://pypi.org/project/daemons/)

## Tests

## Known Issues

## Improvements

- [ ] FIX  config file is needed to exist the daemon. We must be able to do exit the daemon just by providing the pid file

  ```sh
  $ filedispatch -x -p /path/to/pidfile
  ```

- [ ] ADD test to sending over ftp.
- [ ] ADD cli option to decide to keep or remove source after sending complete.
- [ ] ADD cli option to specify the database location.
- [ ] ADD Support to other file sending over HTTP, technics
- [ ] ADD Support to file sending over SSH.
- [ ] ADD Support to many-many relationship between file extension and destination.
- [ ] ADD Support to watching more than one source.
- [ ] ADD pattern matching on processing. That will, for example, let us:
    - exclude some file that match a pattern.
    - Find destination by pattern matching, not only by extension.
- [ ] ADD Support to on-demand compression.
- [ ] ADD Support to text-mining and machine-learning classification algorithm for better experience.
- [ ] ADD a front-end to the log's API.
- [ ] ADD Support to Chart Analysis to view daily, weekly and monthly analysis curve of ours activities.


#### TODOS

- [ ] Rewrite tests. currently unit tests looks more like integration tests than unit tests (lot of components mocking). We want to fix that.
- [ ] Rewrite config parsing components to let it behave as a service we request configuration from.
- [ ] Support project level log configuration (in a yaml file)
- [ ] Look for code to clean and refactor.
- [ ] Reformat the config file to make it more generic to support, excluding some files or directories using full path or pattern.
- [ ] Clean commit on main branch and update the CHANGELOG.
- [ ] Add information on the file creation and last update dates.
- [ ] Treat (filename, destination) as a Message (Add a Message Dataclass)

# File Dispatch

**filedispath** is a simple, configurable, async based and user-friendly cli app
for automatic file organization. It listens to a configured source folder for
new files and copy or move them to the appropriate destination according to
the configuration file.


## Project structure

```
├── src
│   ├── api
│   ├── cli.py
│   ├── config.py
│   ├── exchange.py
│   ├── notifiers.py
│   ├── routers.py
│   ├── schemas.py
│   ├── utils.py
│   └── workers.py
├── tests
│   ├── integration
│   ├── unit
│   ├── base.py
│   ├── conftest.py
│   ├── factories.py
├── CHANGELOG.md
├── config.example.yml
├── CONTRIBUTE.md
├── LICENCE
├── Makefile
├── poetry.lock
├── pyproject.toml
├── pytest.ini
├── README.md
└── run.py
```

## Usage

### Monitor running services [source](https://pypi.org/project/aiomonitor-ng/)
connect to aiomonitor telnet server by using `nc` utility or other telnet client.
```shell
nc 127.0.0.1 50101
```

### filedispatch cli
```shell
usage: filedispatch [--with-webapp] [-m] [-x] [--log-level LOG_LEVEL] [--db DB] [--log-file LOG_FILE] [-p PID_FILE] [--server-url SERVER_URL] [--endpoint ENDPOINT] -c CONFIG [--help]
                    [--version]

filedispath is a simple, configurable, async based and user-friendly cli app for automatic file organization. It listens to a configured source folder for new files and copy or move
them to the appropriate destination according to the configuration file.

options:
  --with-webapp         Launch the embedded web app (type:bool default:False)
  -m, --move            Move files (type:bool default:False)
  -x, --exit            Exit the app (type:bool default:False)
  --log-level LOG_LEVEL
                        Set the log level (type:LogLevel default:INFO)
  --db DB               database file path (type:Optional[Path] default:None)
  --log-file LOG_FILE   log file path (type:Optional[Path] default:None)
  -p PID_FILE, --pid-file PID_FILE
                        pid file path (type:Optional[Path] default:None)
  --server-url SERVER_URL
                        webapp host url (type:Optional[HttpUrl] default:None)
  --endpoint ENDPOINT   webapp endpoint to post log to. (type:Optional[Path] default:api/v1/logs)
  -c CONFIG, --config CONFIG
                        config file path (type:FilePath required=True)
  --help                Print Help and Exit
  --version             show program's version number and exit
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

## Installation
1. Clone the repository
2. Follow steps [poetry]()https://python-poetry.org/docs/#installation to install poetry on your machine
3. Create a virtualenv `python -m venv venv` (optional, but I highly recommend it) and activate it with `source venv/bin/activate` 
4. In the project root directory run `poertry build` and `poetry install`.
5. Done, you can start using filedispatch, I hope you will enjoy using it.

## Features

+ Support local file copy 
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
- [ ] REMOVE the coupling between logs production and logs serving (we may produce data even if --with-webapp is False.)
- [ ] ADD Support to other file sending over HTTP, technics
- [ ] ADD Support to file sending over SSH.
- [ ] ADD Support to many-many relationship between file extension and destination.
- [ ] ADD pattern matching on processing. That will, for example, let us:
    - exclude some file that match a pattern.
    - Find destination by pattern matching, not only by extension.
- [ ] ADD Support to on-demand compression.
- [ ] ADD Support to text-mining and machine-learning classification algorithm for better experience.
- [ ] ADD a front-end to the log's API.
- [ ] ADD Support to Chart Analysis to view daily, weekly and monthly analysis curve of ours activities.
- [ ] Reformat the config file to make it more generic to support, excluding some files or directories using full path or pattern.
- [ ] Clean commit on main branch and update the CHANGELOG.
- [ ] Add file creation date and last update dates to api payload.

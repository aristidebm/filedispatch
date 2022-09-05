import math
import os
from enum import Enum
from typing import Union
from pathlib import Path

import aiofiles
from pydantic import (
    parse_obj_as,
    HttpUrl,
    FileUrl,
    stricturl,
    error_wrappers,
)


__all__ = [
    "get_protocol",
    "get_filesize",
    "get_payload",
    "PATH",
    "StatusEnum",
    "ProtocolEnum",
]

FtpUrl = stricturl(allowed_schemes=["ftp", "sftp"])
FIELDS = dict(file=FileUrl, http=HttpUrl, ftp=FtpUrl)
PATH = Union[str, Path]


class StatusEnum(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class OrderingEnum(str, Enum):
    CREATED = "created"
    REVERSED_CREATED = "-created"
    BYTE_SIZE = "byte_size"
    REVERSED_BYTE_SIZE = "-byte_size"


class ProtocolEnum(str, Enum):
    file = "file"
    http = "http"
    ftp = "ftp"


def get_protocol(url: str) -> str:
    # Pydantic regexp consider http://localhost:8080 as an invalid http url
    url = clean_url(url)
    for k, f in FIELDS.items():
        try:
            parse_obj_as(f, url)
            return k
        except error_wrappers.ValidationError:
            continue
    return "file"


def clean_url(url: PATH) -> PATH:
    # Pydantic regexp consider http://localhost:8080 as an invalid http url
    str_url = str(url)

    if (
        str_url.startswith("http")
        or str_url.startswith("ftp")
        or str_url.startswith("sftp")
    ):
        str_url = url.replace("localhost", "127.0.0.1")

    return Path(str_url) if isinstance(url, Path) else str_url


async def get_filesize(filename):
    suffix = ["KB", "MB", "GB", "TB"]
    quot = byte_size = await aiofiles.os.path.getsize(filename)
    size = None
    idx = -1

    while math.floor(quot):
        size, quot = quot, quot / 1024
        idx += 1
        # stop on terabytes
        if idx == len(suffix) - 1:
            break

    if size:
        size = f"{size: .2f} {suffix[idx]}"
    else:
        size = f"{byte_size / 1024: .2f} {suffix[0]}"

    return size, byte_size


async def get_payload(filename, destination, status, processor, reason=None):
    import src.schema  # FIXME: Fix it just temporary solution

    extension = os.path.splitext(filename)[1].removeprefix(".")

    try:
        # Skip file size fetching if the file is not accessible.
        _size, _byte_size = await get_filesize(filename)
    except OSError:
        _size = None
        _byte_size = None

    return src.schema.WriteOnlyLogEntry(
        filename=os.path.basename(filename),
        destination=str(destination),
        source=os.path.dirname(filename),
        extension=extension,
        processor=processor,
        protocol=ProtocolEnum[get_protocol(destination)],
        status=status,
        size=_size,
        byte_size=_byte_size,
        reason=reason,
    ).dict()

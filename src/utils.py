import math
import os
from datetime import datetime
from enum import Enum
from typing import Union, Optional
from pathlib import Path
from uuid import uuid4, UUID

import aiofiles
from pydantic import (
    parse_obj_as,
    HttpUrl,
    FileUrl,
    stricturl,
    error_wrappers,
    BaseModel,
    Field as PydanticField,
    constr,
)

__all__ = [
    "get_protocol",
    "get_filesize",
    "get_payload",
    "PATH",
    "LogEntry",
    "StatusEnum",
    "ProtocolEnum",
]

FtpUrl = stricturl(allowed_schemes=["ftp", "sftp"])
FIELDS = dict(file=FileUrl, http=HttpUrl, ftp=FtpUrl)
PATH = Union[str, Path]


class StatusEnum(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ProtocolEnum(str, Enum):
    file = "file"
    http = "http"
    ftp = "ftp"


class LogEntry(BaseModel):
    id: UUID = PydanticField(default_factory=uuid4)
    filename: constr(max_length=255)
    source: constr(max_length=255)
    destination: constr(max_length=255)
    extension: constr(max_length=20)
    processor: constr(max_length=255)
    protocol: ProtocolEnum
    status: StatusEnum
    size: Optional[str] = None
    reason: Optional[str] = None
    created: datetime = PydanticField(default_factory=datetime.today)
    updated: datetime = PydanticField(default_factory=datetime.today)


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
    quot = st_size = await aiofiles.os.path.getsize(filename)
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
        size = f"{st_size / 1024: .2f} {suffix[0]}"

    return size


async def get_payload(filename, destination, status, processor, reason=None):
    extension = os.path.splitext(filename)[1].removeprefix(".")

    try:
        # Skip file size fetching if the file is not accessible.
        _size = await get_filesize(filename)
    except OSError:
        _size = None

    return LogEntry(
        filename=os.path.basename(filename),
        destination=str(destination),
        source=os.path.dirname(filename),
        extension=extension,
        processor=processor,
        protocol=ProtocolEnum[get_protocol(destination)],
        status=status,
        size=_size,
        reason=reason,
    ).dict()

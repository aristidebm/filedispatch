from typing import Union
from pathlib import Path

from pydantic import parse_obj_as, HttpUrl, FileUrl, stricturl, error_wrappers

__all__ = [
    "get_protocol",
    "PATH",
]

FtpUrl = stricturl(allowed_schemes=["ftp"])
FIELDS = dict(file=FileUrl, http=HttpUrl, ftp=FtpUrl)
PATH = Union[str, Path]


def get_protocol(url: str) -> str:
    for k, f in FIELDS.items():
        try:
            parse_obj_as(f, url)
            return k
        except error_wrappers.ValidationError:
            continue
    return "file"

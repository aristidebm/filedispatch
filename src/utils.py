from typing import Union
from pathlib import Path

from pydantic import parse_obj_as, HttpUrl, FileUrl, stricturl, error_wrappers

__all__ = [
    "get_protocol",
    "PATH",
]

FtpUrl = stricturl(allowed_schemes=["ftp", "sftp"])
FIELDS = dict(file=FileUrl, http=HttpUrl, ftp=FtpUrl)
PATH = Union[str, Path]


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

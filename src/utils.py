from pydantic import parse_obj_as, HttpUrl, FileUrl, stricturl, error_wrappers

FtpUrl = stricturl(allowed_schemes=["ftp"])
FIELDS = dict(file=FileUrl, http=HttpUrl, ftp=FtpUrl)


def get_protocol(url: str) -> str:
    for k, f in FIELDS.items():
        try:
            parse_obj_as(f, url)
            return k
        except error_wrappers.ValidationError:
            continue
    return "file"

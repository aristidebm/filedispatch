import re
from typing import Any

from pydantic_factories import ModelFactory

from src.schema import WriteOnlyLogEntry
from src.utils import FtpUrl


class LogEntryFactory(ModelFactory):
    __model__ = WriteOnlyLogEntry

    @classmethod
    def get_mock_value(cls, field_type: Any) -> Any:
        """Add our custom mock value."""
        if field_type is FtpUrl:
            return cls._get_faker().url(schemes=["ftp", "sftp"])

        return super().get_mock_value(field_type)

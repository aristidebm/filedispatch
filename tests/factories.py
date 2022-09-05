from pydantic_factories import ModelFactory

from src.schema import WriteOnlyLogEntry


class LogEntryFactory(ModelFactory):
    __model__ = WriteOnlyLogEntry

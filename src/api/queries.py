import operator
import uuid
from datetime import datetime
from pypika import SQLLiteQuery as Query, Table, Field, Column
from pypika.terms import PyformatParameter as Parameter

# Filtres
# --------------------------------------
# - status
# - protocol
# - destination
# - size(byte_size)
# - created(datetime)
# - size(byte_size)__lte
# - size(byte_size)__gte
# - created__lte
# - created__gte

# Sort
# ---------------------------------------
# - ordering=(-size/size/-created/created)

LogEntry = Table("log_entries")

CreateTableQuery = (
    Query.create_table(LogEntry)
    .columns(
        Column("id", "BLOB", nullable=False),
        Column("filename", "VARCHAR(255)", nullable=False),
        Column("source", "VARCHAR(255)", nullable=False),
        Column("destination", "VARCHAR(255)", nullable=False),
        Column("extension", "VARCHAR(20)", nullable=False),
        Column("worker", "VARCHAR(255)", nullable=False),
        Column("protocol", "VARCHAR(255)", nullable=False),
        Column("status", "VARCHAR(20)", nullable=False),
        Column("size", "VARCHAR(255)", nullable=True),
        Column("byte_size", "REAL", nullable=True),
        Column("reason", "TEXT", nullable=True, default=None),
        Column("created", "DATETIME", nullable=False),
    )
    .if_not_exists()
    .primary_key("id")
)

# https://pypika.readthedocs.io/en/latest/2_tutorial.html#parametrized-queries

CreateLogEntryQuery = Query.into(LogEntry).insert(
    Parameter("id"),
    Parameter("filename"),
    Parameter("source"),
    Parameter("destination"),
    Parameter("extension"),
    Parameter("worker"),
    Parameter("protocol"),
    Parameter("status"),
    Parameter("size"),
    Parameter("byte_size"),
    Parameter("reason"),
    Parameter("created"),
)


ListLogEntriesQuery = Query.from_(LogEntry).select(
    LogEntry.id,
    LogEntry.filename,
    LogEntry.source,
    LogEntry.destination,
    LogEntry.extension,
    LogEntry.worker,
    LogEntry.protocol,
    LogEntry.status,
    LogEntry.size,
    LogEntry.byte_size,
    LogEntry.reason,
    LogEntry.created,
)

RetrieveLogEntryQuery = (
    Query.from_(LogEntry)
    .select(
        LogEntry.id,
        LogEntry.filename,
        LogEntry.source,
        LogEntry.destination,
        LogEntry.extension,
        LogEntry.worker,
        LogEntry.protocol,
        LogEntry.status,
        LogEntry.size,
        LogEntry.byte_size,
        LogEntry.reason,
        LogEntry.created,
    )
    .where(LogEntry.id == Parameter("id"))
)

DeleteLogEntryQuery = (
    Query.from_(LogEntry).delete().where(LogEntry.id == Parameter("id"))
)

DeleteLogEntriesQuery = Query.from_(LogEntry).delete()

DropTableQuery = Query.drop_table(LogEntry)

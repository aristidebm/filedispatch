import operator
import uuid
from datetime import datetime
from pypika import SQLLiteQuery as Query, Table, Field, Column
from pypika.terms import ValueWrapper, PyformatParameter as Parameter

# Filtres
# --------------------------------------
# - status
# - processor
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

LogEntry = Table("LogEntry")

CreateTableQuery = (
    Query.create_table(LogEntry)
    .columns(
        Column("id", "BLOB", nullable=False, default=ValueWrapper(uuid.uuid4())),
        Column("filename", "VARCHAR(255)", nullable=False),
        Column("destination", "VARCHAR(255)", nullable=False),
        Column("extension", "VARCHAR(20)", nullable=False),
        Column("processor", "VARCHAR(255)", nullable=False),
        Column("size", "VARCHAR(255)", nullable=True),
        Column("byte_size", "REAL", nullable=True),
        Column("status", "VARCHAR(20)", nullable=False),
        Column("reason", "TEXT", nullable=True, default=None),
        Column(
            "created",
            "DATETIME",
            nullable=False,
            default=ValueWrapper(datetime.today()),
        ),
        Column(
            "updated",
            "DATETIME",
            nullable=False,
            default=ValueWrapper(datetime.today()),
        ),
    )
    .if_not_exists()
    .primary_key("id")
)

# https://pypika.readthedocs.io/en/latest/2_tutorial.html#parametrized-queries

CreateLogEntry = Query.into(LogEntry).insert(
    Parameter("filename"),
    Parameter("extension"),
    Parameter("processor"),
    Parameter("byte_size"),
    Parameter("size"),
    Parameter("status"),
    Parameter("reason"),
)


ListLogEntries = Query.from_(LogEntry).select(
    LogEntry.id,
    LogEntry.filename,
    LogEntry.extension,
    LogEntry.processor,
    LogEntry.size,
    LogEntry.byte_size,
    LogEntry.status,
    LogEntry.reason,
    LogEntry.created,
)

RetrieveLogEntry = (
    Query.from_(LogEntry)
    .select(
        LogEntry.id,
        LogEntry.filename,
        LogEntry.extension,
        LogEntry.processor,
        LogEntry.size,
        LogEntry.byte_size,
        LogEntry.status,
        LogEntry.reason,
        LogEntry.created,
    )
    .where(LogEntry.id == Parameter("id"))
)

DeleteLogEntry = Query.from_(LogEntry).delete().where(LogEntry.id == Parameter("id"))

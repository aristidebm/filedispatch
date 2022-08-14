import uuid
from datetime import datetime
from pypika import SQLLiteQuery as Query, Table, Field, Column
from pypika.terms import ValueWrapper

TableQuery = (
    Query.create_table("LogEntry")
    .columns(
        Column("id", "BLOB", nullable=False, default=ValueWrapper(uuid.uuid4())),
        Column("filename", "VARCHAR(255)", nullable=False),
        Column("destination", "VARCHAR(255)", nullable=False),
        Column("extention", "VARCHAR(20)", nullable=False),
        Column("processor", "VARCHAR(255)", nullable=False),
        Column("size", "REAL", nullable=True),
        # FIXME: Find how to use CHECK with pypika (SUCCEEDED|FAILED)
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

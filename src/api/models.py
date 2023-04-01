import datetime
import json
import operator
import uuid
from collections import namedtuple
from typing import Mapping, List
from uuid import UUID

import aiosqlite
from pydantic import parse_obj_as
from pypika import CustomFunction, Order

from src.schema import ReadOnlyLogEntry, WriteOnlyLogEntry, QueryDict

from .queries import (
    CreateTableQuery,
    CreateLogEntryQuery,
    ListLogEntriesQuery,
    RetrieveLogEntryQuery,
    DeleteLogEntryQuery,
    DropTableQuery,
    LogEntry,
)

SQLITE_DATE_CAST = CustomFunction("strftime", ["format", "date"])

LOOKUP_TO_OPERATORS = {
    "gte": operator.ge,
    "lte": operator.le,
    "lt": operator.lt,
    "gt": operator.ge,
    "exact": operator.eq,
}

Filter = namedtuple("Filter", ["field_name", "value", "operator"])


class Dao:
    """
    TODO: Since aiosqlite doesn't provide connection pooling, and keeping a long running connection can
        cause some memory problem we adopt open/close pattern. Another solution is to have one long running
        connection but have different cursors. It is hard to make a decision now, improve letter.
    """

    # FIXME: I Think The method parse_obj_as here https://pydantic-docs.helpmanual.io/usage/models/#model-properties
    #  can help as returning Pydantic models

    def __init__(self, connector=None):
        self._connector = connector

    @property
    def connector(self):
        return self._connector

    @connector.setter
    def connector(self, connector):
        self._connector = connector

    async def fetch_all(self, query_dict: QueryDict) -> List[ReadOnlyLogEntry]:
        query_dict = vars(query_dict)
        query = ListLogEntriesQuery
        ordering = query_dict.pop("ordering", None)
        filters = self._get_filters(query_dict)

        for f in filters:
            f_value = f.value
            f_name = f.field_name
            if f_name.name.startswith("created"):
                # since SQLite doesn't have date type (date are stored as TEXT)
                # we have to mimic the desired behavior, we use SQLite strftime
                # for this purpose.
                f_name = SQLITE_DATE_CAST("%Y-%m-%d", f_name)
            query = query.where(f.operator(f_name, f_value))

        if ordering:
            cleaned_ordering = ordering.value.removeprefix("-")
            if cleaned_ordering == ordering.value:
                query = query.orderby(cleaned_ordering, order=Order.asc)
            else:
                query = query.orderby(cleaned_ordering, order=Order.desc)

        async with self.connector() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query.get_sql()) as cursor:
                rows = await cursor.fetchall()
                return self._get_response_body(rows)

    async def fetch_one(self, pk: UUID) -> ReadOnlyLogEntry:
        query = RetrieveLogEntryQuery.get_sql()
        query = query % self.stringify({"id": pk})

        async with self.connector() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query) as cursor:
                row = await cursor.fetchone()
                data = self._get_response_body([row])
                # returns the first element if it exists.
                for el in data:
                    return el

    async def insert(self, data: WriteOnlyLogEntry) -> ReadOnlyLogEntry:
        data_json = json.loads(data.json())
        async with self.connector() as db:
            query = CreateLogEntryQuery.get_sql()
            context = data_json
            id_ = uuid.uuid4()
            context["id"] = id_
            context["created"] = datetime.datetime.now().isoformat()
            context = self.stringify(context)
            query = query % context
            await db.execute(query)
            await db.commit()

        return await self.fetch_one(pk=id_)

    async def delete(self, pk: UUID) -> None:
        async with self.connector() as db:
            query = DeleteLogEntryQuery.get_sql()
            query = query % self.stringify({"id": pk})
            await db.execute(query)
            await db.commit()

    async def create_table(self):
        async with self.connector() as db:
            query = CreateTableQuery.get_sql()
            await db.execute(query)
            await db.commit()

    async def drop_table(self):
        async with self.connector() as db:
            query = DropTableQuery.get_sql()
            await db.execute(query)
            await db.commit()

    def _get_filters(self, data: Mapping) -> List[Filter]:
        filters = []
        for f, value in data.items():
            if value:
                lookup = "exact"
                if len(s := f.split("__")) > 1:
                    f, lookup = s

                op_ = LOOKUP_TO_OPERATORS.get(lookup, "exact")

                # We need Criterion class for filtering, when using
                # Table instance in a Query it is automatically created
                # for us.
                if not (f := getattr(LogEntry, f, None)):
                    continue

                filters.append(Filter(field_name=f, value=value, operator=op_))

        return filters

    def stringify(self, context):
        return {k: "NULL" if v is None else f"'{v}'" for k, v in context.items()}

    def _get_response_body(self, rows: List[aiosqlite.Row]) -> List[ReadOnlyLogEntry]:
        # remove eventual None from rows.
        rows = filter(None, rows)
        return [parse_obj_as(ReadOnlyLogEntry, row) for row in rows]

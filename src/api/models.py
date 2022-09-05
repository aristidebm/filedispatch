# create LogEntry Table here, that will contains logs informations to be exposed on the api. Table to be modeled.
# Check if we can use this query builder https://pypi.org/project/qwery/ with https://pypi.org/project/aiosqlite/

# It can be a good project to write a query-builder like https://github.com/kayak/pypika that cooled accept pydantic model
# for table schema this can be a good start  https://github.com/rafalstapinski/p3orm

# L'idee est de
# + Construire juste un wrapper qui converti les tables pydantic en table pypika et ensuite (pypika sais bien faire ce qu'il faut)
# + Ajouter des equivalent de method asynchrones aux method existante de pypika
# + Ensuite en sortie, on veut bien avoir des models pydantic car, plus facile a manipuler en python qu'avec les autre.

# ----- Choix techniques ------------

# En attendant je vais utiliser :
# + Pypika pour la generation de requeste sql https://github.com/kayak/pypika
# + aiosqlite pour l'execution des requetes https://github.com/omnilib/aiosqlite en mode asynchrone.
# + Il faut faire la modelisation du LogEntry.

import operator
from collections import namedtuple
from pathlib import Path
from typing import Mapping, List
from functools import partial
from uuid import UUID

import aiosqlite
from pydantic import parse_obj_as, ValidationError

from src.schema import ReadOnlyLogEntry, WriteOnlyLogEntry, QueryDict

from .queries import (
    CreateTableQuery,
    CreateLogEntry,
    ListLogEntries,
    RetrieveLogEntry,
    DeleteLogEntry,
    LogEntry,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
connect = partial(aiosqlite.connect, BASE_DIR / "db.sqlite3")


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
    #  can help as returning Pyandic models

    async def fetch_all(self, query_dict: QueryDict) -> List[ReadOnlyLogEntry]:
        query_dict = vars(query_dict)
        query = ListLogEntries
        filters = self._get_filters(query_dict)

        for f in filters:
            query = query.where(f.operator(f.field_name, f.value))

        async with connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query.get_sql()) as cursor:
                rows = await cursor.fetchall()
                return self._get_response_body(rows)

    async def fetch_one(self, pk: UUID) -> ReadOnlyLogEntry:
        query = RetrieveLogEntry.get_sql()
        query = query % {LogEntry.id: pk}

        async with connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query) as cursor:
                row = await cursor.fetcone()
                data = self._get_response_body([row])
                return data[0]

    async def insert(self, data: WriteOnlyLogEntry) -> ReadOnlyLogEntry:
        def _get_fields(data: Mapping):
            fields = {}
            for key in data:
                f = getattr(LogEntry, key, None)
                fields[f] = data[key]
            return fields

        async with connect() as db:
            query = CreateLogEntry.get_sql()
            query = query % _get_fields(data.dict())
            async with db.execute(query) as cursor:
                last_rowid = cursor.lastrowid
                return await self.fetch_one(pk=last_rowid)

    async def delete(self, pk: UUID) -> None:
        async with connect() as db:
            query = DeleteLogEntry.get_sql()
            query = query % {LogEntry.id: pk}
            async with db.execute(query):
                ...

    def _get_filters(self, data: Mapping) -> List[Filter]:
        filters = []
        for f, value in data.items():
            if value:
                lookup = "exact"
                if len(s := f.split("__")) > 1:
                    lookup = s[1]

                op_ = LOOKUP_TO_OPERATORS.get(lookup, "exact")

                # We need Criterion class for filtering, when using
                # Table instance in a Query it is automatically created
                # for us.
                if f := getattr(LogEntry, f, None) is None:
                    continue

                filters.append(Filter(field_name=f, value=value, operator=op_))

        return filters

    def _get_response_body(self, rows: List[aiosqlite.Row]) -> List[ReadOnlyLogEntry]:
        return [parse_obj_as(ReadOnlyLogEntry, row) for row in rows]

# create LogEntry Table here, that will contains logs informations to be exposed on the api. Table to be modeled.
# Check if we can use this query builder https://pypi.org/project/qwery/ with https://pypi.org/project/aiosqlite/

# It can be a good project to write a query-builder like https://github.com/kayak/pypika that cooled accept pydantic model
# for table schema this can be a good start  https://github.com/rafalstapinski/p3orm

# L'idee est de
# + Construire juste un wrapper qui converti les tables pydantic en table pypika et ensuite (pypika sais bien faire ce qu'il faut)
# + Ajouter des equivalent de method asynchrones aux method existante de pypika
# + Ensuite en sortie, on veut bien avoir des models pydantic car, plus facile a manipuler en python qu'avec les autre.

##### ----- Choix techniques ------------

# En attendant je vais utiliser :
# + Pypika pour la generation de requeste sql https://github.com/kayak/pypika
# + aiosqlite pour l'execution des requetes https://github.com/omnilib/aiosqlite en mode asynchrone.
# + Il faut faire la modelisation du LogEntry.

# Champs de la table
# --------------------

# + filename
# + destination
# + file Extention
# + file size
# + processor used.
# + operaton status (SUCCEEDED/FAILED)
# + reason
# + created
# + updated
from enum import Enum
from pathlib import Path
from typing import Mapping, Optional
from functools import cached_property, partial
from uuid import UUID, uuid4

import aiosqlite
from pydantic import BaseModel, Field as PydanticField, constr

from .queries import *  # noqa

BASE_DIR = Path(__file__).resolve().parent.parent.parent
connect = partial(aiosqlite.connect, BASE_DIR / "db.sqlite3")


class StatusEnum(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ProtocolEnum(str, Enum):
    file = "file"
    http = "http"
    ftp = "ftp"


class LogEntry(BaseModel):
    id: UUID = PydanticField(default_factory=uuid4)
    filename: constr(max_length=255)
    source: constr(max_length=255)
    destination: constr(max_length=255)
    extension: constr(max_length=20)
    processor: constr(max_length=255)
    protocol: ProtocolEnum
    status: StatusEnum
    size: str
    reason: Optional[str] = None
    created: datetime = PydanticField(default_factory=datetime.today)
    updated: datetime = PydanticField(default_factory=datetime.today)


class Dao:
    """
    TODO: Since aiosqlite doesn't provide connection pooling, and keeping a long running connection can
        cause some memory problem we adopt open/close pattern. Another solution is to have one long running
        connection but have different cursors. It is hard to make a decision now, improve letter.
    """

    # FIXME: I Think The method parse_obj_as here https://pydantic-docs.helpmanual.io/usage/models/#model-properties
    #  can help as returning Pyandic models

    async def fetch_all(self, filters: Mapping):
        async with connect() as conn:
            pass

    async def fetch_one(self, pk):
        async with connect() as conn:
            await conn.execute()

    async def insert(self, data):
        async with connect() as conn:
            await conn.execute()

    async def delete(self, pk):
        async with connect() as conn:
            await conn.execute()

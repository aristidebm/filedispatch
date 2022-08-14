from decimal import Decimal
from uuid import UUID
from typing import Optional
from datetime import datetime

from pydantic import Field

from aiohttp import web
from aiohttp_pydantic import PydanticView

from .models import Dao, LogEntry, StatusEnum  # noqa

routes = web.RouteTableDef()


@routes.view("/api/logs")
class LogsView(PydanticView):

    dao: Dao = Dao()

    async def get(
        self,
        id: Optional[UUID] = Field(None, description="Retrieves Log by ID"),
        status: Optional[StatusEnum] = Field(None, description="Filter logs by status"),
        destination: Optional[str] = Field(
            None, description="Filter logs by file destination"
        ),
        size__lte: Optional[Decimal] = Field(
            None, description="Filter logs by size less than or equal"
        ),
        size__gte: Optional[Decimal] = Field(
            None, description="Filter logs by size greater than or equal"
        ),
        filename: Optional[str] = Field(
            None, description="Filter logs by file filename"
        ),
        extension: Optional[str] = Field(
            None, description="Filter logs by file extension"
        ),
        protocol: Optional[str] = Field(
            None, description="Filter logs by protocol used to send the file"
        ),
        created__lte: Optional[datetime] = Field(
            None, description="Filter logs by creation date less than or equal"
        ),
        created__gte: Optional[datetime] = Field(
            None, description="Filter logs by creation date greater than or equal"
        ),
    ):
        data = await self.dao.fetch_one()
        return web.json_response(data)

    async def post(self, log: LogEntry):
        ...

    async def delete(self, id: UUID = Field(..., description="Log ID")):
        ...

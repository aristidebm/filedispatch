from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import List, Union, Any, Optional

from pydantic import Field

from aiohttp import web
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404

from src.schema import ReadOnlyLogEntry, WriteOnlyLogEntry, QueryDict, Error
from src.utils import StatusEnum, OrderingEnum
from src.api.models import Dao

routes = web.RouteTableDef()


class BasicView(PydanticView):
    dao: Dao = Dao()


@routes.view(r"/api/v1/logs", name="logs_list")
class ListView(BasicView):
    # I don't if doing think like so (passing filters instead of key value pairs, key = Field()) will work.
    async def get(self, query_dict: QueryDict) -> r200[List[ReadOnlyLogEntry]]:
        data = await self.dao.fetch_all(query_dict)
        data = [item.dict() for item in data]
        return web.json_response(data)

    async def post(self, data: WriteOnlyLogEntry) -> r201[ReadOnlyLogEntry]:
        data = await self.dao.insert(data)
        return web.json_response(data.dict())


@routes.view(r"/api/v1/logs/{id}", name="logs_detail")
class DetailView(BasicView):
    async def get(
        self, id: UUID = Field(..., description="Log ID")
    ) -> Union[r200[ReadOnlyLogEntry], r404[Error]]:
        data = await self.dao.fetch_one(pk=id)
        return web.json_response(data=data.dict())

    async def delete(self, id: UUID = Field(..., description="Log ID")) -> r204[Any]:
        await self.dao.delete(pk=id)
        return web.json_response(status=204)

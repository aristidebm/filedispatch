import json
from uuid import UUID
from typing import List, Union, Any

from pydantic import Field

from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPNoContent
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404

from src.schema import ReadOnlyLogEntry, WriteOnlyLogEntry, QueryDict, Error
from src.utils import move_dict_key_to_top, JSON_CONTENT_TYPE
from src.api.models import Dao

routes = web.RouteTableDef()


class BasicView(PydanticView):
    ...


@routes.view(r"/api/v1/logs", name="logs_list")
class ListView(BasicView):
    # I don't if doing think like so (passing filters instead of key value pairs, key = Field()) will work.
    async def get(self, query_dict: QueryDict) -> r200[List[ReadOnlyLogEntry]]:
        dao = self.request.app["dao"]
        data = await dao.fetch_all(query_dict)
        data = [
            move_dict_key_to_top(json.loads(item.json()), key="id") for item in data
        ]
        return web.json_response(data, status=200, content_type=JSON_CONTENT_TYPE)

    async def post(self, data: WriteOnlyLogEntry) -> r201[ReadOnlyLogEntry]:
        dao = self.request.app["dao"]
        data = await dao.insert(data)
        data = json.loads(data.json())
        data = move_dict_key_to_top(data, "id")
        return web.json_response(data, status=201, content_type=JSON_CONTENT_TYPE)


@routes.view(r"/api/v1/logs/{id}", name="logs_detail")
class DetailView(BasicView):
    async def get(
        self, id: UUID = Field(..., description="Log ID"), /  # noqa W504
    ) -> Union[r200[ReadOnlyLogEntry], r404[Error]]:
        dao = self.request.app["dao"]
        data = await dao.fetch_one(pk=id)
        if not data:
            # HttpException class inherit from Response, so we can
            # pass content_type
            raise HTTPNotFound(content_type=JSON_CONTENT_TYPE)
        data = json.loads(data.json())

        data = move_dict_key_to_top(data, "id")
        return web.json_response(data=data, status=200, content_type=JSON_CONTENT_TYPE)

    async def delete(self, id: UUID = Field(..., description="Log ID"), /) -> r204[Any]:
        dao = self.request.app["dao"]
        await dao.delete(pk=id)
        raise HTTPNoContent(content_type=JSON_CONTENT_TYPE)

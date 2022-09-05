import pytest

from tests.factories import LogEntryFactory
from src.api.server import make_app

pytestmark = pytest.mark.api


@pytest.mark.asyncio
async def test_create_log_entry(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    payload = LogEntryFactory.build().dict()
    await client.post(app.router["logs_list"].url_for(), data=payload)


@pytest.mark.asyncio
async def test_get_all_log_entries(aiohttp_client):
    # create a log entry here.
    app = make_app()
    client = await aiohttp_client(app)
    await client.get(app.router["logs_list"].url_for())


@pytest.mark.asyncio
async def test_get_log_entries_by_filters(aiohttp_client):
    # create a log entry here.
    app = make_app()
    payload = {}
    client = await aiohttp_client(app)
    await client.get(app.router["logs_list"].url_for(), parama=payload)


@pytest.mark.asyncio
async def test_get_log_entry_by_id(aiohttp_client):
    # create a log entry here.
    id_ = str(1)
    app = make_app()
    payload = {}
    client = await aiohttp_client(app)
    await client.get(app.router["logs_detail"].url_for(id=id_), params=payload)


@pytest.mark.asyncio
async def test_delete_log_entry(aiohttp_client):
    # create a log entry here.
    id_ = str(1)
    app = make_app()
    payload = {}
    client = await aiohttp_client(app)
    await client.delete(app.router["logs_detail"].url_for(id=id_), params=payload)

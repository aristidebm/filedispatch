import datetime
import decimal
import json
from pathlib import Path

import pytest
import pytest_asyncio

from tests.factories import LogEntryFactory
from src.api.server import make_app
from src.api.queries import CreateTableQuery, DropTableQuery

pytestmark = pytest.mark.api

BASE_URL = Path(__file__).parent.parent.parent


@pytest_asyncio.fixture
async def client(aiohttp_client, tmp_path):
    db = tmp_path / "test-db.sqlite3"
    db.touch()
    app = make_app(db=db)
    dao = app["dao"]
    await dao.create_table()
    clt = await aiohttp_client(app)

    yield clt

    await dao.drop_table()


@pytest.mark.asyncio
async def test_create_log_entry(client):
    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data


@pytest.mark.asyncio
async def test_get_all_log_entries(client):
    # create a log entry here.

    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    rs = await client.get(client.app.router["logs_list"].url_for())
    assert rs.status == 200

    data = await rs.json()
    data = data[0]
    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data


@pytest.mark.asyncio
async def test_get_log_entries_by_status(client):
    # create a log entry here.

    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    filters = {"status": payload["status"]}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200

    data = await rs.json()
    data = data[0]

    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data

    filters = {"status": "fake"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 400

    status = "SUCCEEDED" if payload["status"] == "FAILED" else "FAILED"
    filters = {"status": status}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert not data


@pytest.mark.asyncio
async def test_get_log_entries_by_destination(client):
    # create a log entry here.
    payload = json.loads(LogEntryFactory.build().json())
    path = "/mnt/download/video"
    payload["destination"] = path
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    filters = {"destination": path}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200

    data = await rs.json()
    data = data[0]

    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data

    filters = {"destination": "fake"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_log_entries_by_protocol(client):
    # create a log entry here.

    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    filters = {"protocol": payload["protocol"]}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200

    data = await rs.json()
    data = data[0]

    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data

    filters = {"protocol": "fake"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert not data


@pytest.mark.asyncio
async def test_get_log_entries_by_created(client):
    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    created = data["created"].split("T")[0]
    filters = {"created": created}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200

    data = await rs.json()
    data = data[0]

    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data

    filters = {"created__lte": created}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 1

    filters = {"created__gte": created}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 1

    created = (
        (datetime.datetime.fromisoformat(created) + datetime.timedelta(days=2))
        .date()
        .isoformat()
    )
    filters = {"created": created}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 0

    # make sure we only support iso-format
    filters = {"created": "12/20/2023"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 400


@pytest.mark.asyncio
async def test_get_log_entries_by_byte_size(client):
    payload = json.loads(LogEntryFactory.build().json())
    payload["byte_size"] = decimal.Decimal("1000000.0").__str__()
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    size = data["byte_size"]
    filters = {"byte_size": size}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200

    data = await rs.json()
    data = data[0]

    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data

    filters = {"byte_size__lte": size}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 1

    filters = {"byte_size__gte": size}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 1

    byte_size = size + 1
    filters = {"byte_size": byte_size}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 200
    data = await rs.json()
    assert len(data) == 0

    # make sure we only support iso-format
    filters = {"created": "Not a Deicmal"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=filters)
    assert rs.status == 400


@pytest.mark.asyncio
async def test_ordering_log_entries_by_creation(client):
    payload = json.loads(LogEntryFactory.build().json())
    payload["byte_size"] = decimal.Decimal("1000000.0").__str__()
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    log_1 = data["id"]

    payload = json.loads(LogEntryFactory.build().json())
    payload["byte_size"] = decimal.Decimal("2200000.0").__str__()
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    log_2 = data["id"]

    ordering = {"ordering": "-byte_size"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=ordering)
    assert rs.status == 200
    data = await rs.json()

    assert log_2 == data[0]["id"]
    assert log_1 == data[1]["id"]

    ordering = {"ordering": "byte_size"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=ordering)
    assert rs.status == 200
    data = await rs.json()

    assert log_1 == data[0]["id"]
    assert log_2 == data[1]["id"]


@pytest.mark.asyncio
async def test_ordering_log_entries_by_size(client):
    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    log_1 = data["id"]

    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201

    data = await rs.json()
    log_2 = data["id"]

    ordering = {"ordering": "-created"}
    rs = await client.get(client.app.router["logs_list"].url_for(), params=ordering)
    assert rs.status == 200
    data = await rs.json()

    assert log_2 == data[0]["id"]
    assert log_1 == data[1]["id"]


@pytest.mark.asyncio
async def test_get_log_entry_by_id(client):
    # create a log entry here.

    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201
    data = await rs.json()

    rs = await client.get(client.app.router["logs_detail"].url_for(id=data["id"]))
    assert rs.status == 200

    data = await rs.json()

    assert "id" in data
    assert data["filename"] == payload["filename"]
    assert data["source"] == payload["source"]
    assert data["destination"] == payload["destination"]
    assert data["worker"] == payload["worker"]
    assert data["protocol"] == payload["protocol"]
    assert data["status"] == payload["status"]
    assert data["size"] == payload["size"]
    assert data["reason"] == payload["reason"]
    assert "byte_size" in data
    assert "created" in data


@pytest.mark.asyncio
async def test_delete_log_entry(client):
    # create a log entry here.
    payload = json.loads(LogEntryFactory.build().json())
    rs = await client.post(client.app.router["logs_list"].url_for(), json=payload)
    assert rs.status == 201
    data = await rs.json()

    # attempt deletion.
    rs = await client.delete(client.app.router["logs_detail"].url_for(id=data["id"]))
    assert rs.status == 204

    # Make sure the log-entry is successfully deleted.
    rs = await client.get(client.app.router["logs_detail"].url_for(id=data["id"]))
    assert rs.status == 404

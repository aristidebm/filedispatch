import os

import aioftp
from aiohttp import web, hdrs
from aiohttp.web_routedef import RouteDef


def contains(folder, file):
    return os.path.basename(file) in os.listdir(folder)


def make_app(routes=None, status=200, body=None, **kwargs):
    # https://docs.aiohttp.org/en/stable/testing.html?highlight=tests#testing-aiohttp-web-servers
    # routes

    async def healfcheck(request):
        return web.Response(body=b"running ...")

    async def receive_audio(request):
        print(content := await request.content.read())
        return web.Response(body=body or content, status=status)

    routes = routes or []
    routes = routes + [
        RouteDef(method=hdrs.METH_GET, path="/", handler=healfcheck, kwargs={}),
        RouteDef(
            method=hdrs.METH_POST,
            path="/documents/audio",
            handler=receive_audio,
            kwargs={},
        ),
    ]
    app = web.Application()
    app.router.add_routes(routes)
    return app


# source: https://aioftp.readthedocs.io/developer_tutorial.html?highlight=Test#server
class TestServer(aioftp.Server):
    def __init__(self, host=None, port=None, users=None, **kwargs):
        super(TestServer, self).__init__(users=users)
        self._host = host or "127.0.0.1"
        self._port = port or 8021

    @aioftp.ConnectionConditions(
        aioftp.ConnectionConditions.login_required,
        aioftp.ConnectionConditions.passive_server_started,
    )
    async def coll(self, connection, rest):
        @aioftp.ConnectionConditions(
            aioftp.ConnectionConditions.data_connection_made,
            wait=True,
            fail_code="425",
            fail_info="Can't open data connection",
        )
        @aioftp.server.worker
        async def coll_worker(self, connection, rest):
            stream = connection.data_connection
            del connection.data_connection
            async with stream:
                for i in range(count):
                    binary = i.to_bytes(8, "big")
                    await stream.write(binary)
            connection.response("200", "coll transfer done")
            return True

        count = int(rest)
        coro = coll_worker(self, connection, rest)
        task = connection.loop.create_task(coro)
        connection.extra_workers.add(task)
        connection.response("150", "coll transfer started")
        return True

    async def __aenter__(self):
        await self.start(self.host, self.port)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

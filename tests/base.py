import os
import tempfile
from aiohttp import web, hdrs
from aiohttp.web_routedef import RouteDef


def contains(folder, file):
    return os.path.basename(file) in os.listdir(folder)


from aiohttp import web


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

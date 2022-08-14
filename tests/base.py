import os
import tempfile
from aiohttp import web
from aiohttp.web_routedef import RouteDef


def create_file(filesystem, ext="txt", is_file=True):
    source = os.path.join(filesystem.name, "mnt")
    ext = ext.lower().removeprefix(".")
    ext = "." + ext
    if is_file:
        f = tempfile.NamedTemporaryFile(mode="w+b", suffix=ext, dir=source)
        f.flush()
    else:
        f = tempfile.TemporaryDirectory(dir=source)

    return f


def contains(folder, file):
    return os.path.basename(file) in os.listdir(folder)


from aiohttp import web


async def hello(request):
    return web.Response(body=b"Hello, world")


def make_app(routes=None):
    # routes
    async def healfcheck(request):
        return web.Response(body=b"running ...")

    routes = routes or []
    routes = routes + [RouteDef(method="GET", path="/", handler=healfcheck, **{})]
    app = web.Application()
    app.router.add_routes(routes)
    return app

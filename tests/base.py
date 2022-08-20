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


# def make_app(routes=None):
#     # https://docs.aiohttp.org/en/stable/testing.html?highlight=tests#testing-aiohttp-web-servers
#     # routes
#
#     async def healfcheck(request):
#         return web.Response(body=b"running ...")

# async def receive_audio(request):
#     content = await request.content.read()
#     print(content)
#     return web.Response(body=f"Successfully added to {request.path}")
#
# routes = routes or []
# routes = routes + [
#     RouteDef(method="GET", path="/", handler=healfcheck, kwargs={}),
#     RouteDef(
#         method="POST", path="/documents/audio", handler=receive_audio, kwargs={}
#     ),
# ]
# app = web.Application()
# app.router.add_routes(routes)
# return app

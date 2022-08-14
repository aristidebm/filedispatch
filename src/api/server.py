##### --- choix technique ----

# It will be good if we can use this server as runtime dependency (https://github.com/ask/mode#what-is-mode) of file dispatch.
# https://docs.aiohttp.org/en/stable/web_quickstart.html

# The api must expose

# - POST /api/logs/
# - GET /api/logs/
# - GET /api/logs/<id>
# - DELETE /api/logs/<id>

# It must expose filters

# - By creation date
# - By transaction state [SUCCEED|FAILURE]
# - By destination
# - By file size
# - By file extension
# - By file name
# - By used protocol
import asyncio
import logging
import mode
from aiohttp import web
from aiohttp_pydantic import oas
import nest_asyncio

nest_asyncio.apply()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from .views import routes

__version__ = "1.0.0"


class WebServer(mode.Service):
    host: str = "http://127.0.0.1:3002"

    def __init__(self, host=None):
        super().__init__()
        self.host: str = host or self.host

    async def on_started(self) -> None:
        ...
        # aiohttp call loop.run_util_complete on the loop, that generate
        # an error since the loop is already running https://github.com/aio-libs/aiohttp/blob/master/aiohttp/web.py#L447
        # An issue is open here since 2017 # https://github.com/aio-libs/aiohttp/issues/2608
        # loop = asyncio.get_running_loop()

        # normally it permit to run more than on event_loop, but got a weird error socket.gaierror: [Errno -2] Name or service not known
        nest_asyncio.apply()
        web.run_app(self.make_app(), host=self.host)

    async def on_stop(self) -> None:
        pass

    @staticmethod
    def make_app():
        app = web.Application()
        app.add_routes(routes)
        # setup open api documentation as stated here (
        # https://github.com/Maillol/aiohttp-pydantic#add-route-to-generate-open-api-specification-oas)
        oas.setup(
            app,
            url_prefix=f"/api/v{__version__.split('.')[0]}/schema",
            title_spec="File Dispatch Monitoring Api",
            version_spec=__version__,
        )
        return app

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
from functools import cached_property
import asyncio
import mode
from aiohttp import web
from aiohttp_pydantic import oas

import nest_asyncio

# nest_asyncio.apply()

from .views import routes

__version__ = "0.1.0"


class WebServer(mode.Service):
    host: str = "127.0.0.1"
    port: int = 8080
    runner = None

    def __init__(self, host=None, port=None):
        super().__init__()
        self.host: str = host or self.host
        self.port: int = port or self.port

    async def on_started(self) -> None:
        # web.run_app is not only a blocking API (to be run only on synchronous environment, wich is not our case), but
        # also create a new event loop if not provided, and try to apply run_until_complete on provided loop that also
        # generate a Runtime error, loop already running, so we must declare our own asynchronous app runner.
        # https://github.com/aio-libs/aiohttp/blob/master/aiohttp/web.py#L447
        # https://github.com/aio-libs/aiohttp/issues/2608
        self.logger.info("web server is starting ...")
        await self.run_app()

    async def on_stop(self) -> None:
        self.logger.info("web server is shutting down ...")
        await self.runner.cleanup()

    def _make_app(self):
        app = web.Application()
        app.add_routes(routes)
        # setup open api documentation as stated here (
        # https://github.com/Maillol/aiohttp-pydantic#add-route-to-generate-open-api-specification-oas)
        oas.setup(
            app,
            url_prefix=f"/api/v1/schema",
            title_spec="File Dispatch Monitoring Api",
            version_spec=__version__,
        )
        return app

    @cached_property
    def runner(self):
        app = self._make_app()
        runner = web.AppRunner(app, logger=self.logger)
        return runner

    async def run_app(self):
        # https://docs.aiohttp.org/en/stable/web_advanced.html#application-runners
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        while True:
            await asyncio.sleep(3600)  # sleep forever

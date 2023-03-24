# --- choix technique ----

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
from functools import cached_property, partial
import asyncio

import aiosqlite
import mode
from aiohttp import web
from aiohttp_pydantic import oas

from src.utils import PATH, BASE_DIR
from .views import routes
from .models import Dao

__version__ = "0.1.0"


def make_app(db: PATH = None):
    app = web.Application()
    app.add_routes(routes)
    # setup open api documentation as stated here (
    # https://github.com/Maillol/aiohttp-pydantic#add-route-to-generate-open-api-specification-oas)
    oas.setup(
        app,
        url_prefix="/api/v1/schema",
        title_spec="File Dispatch Monitoring Api",
        version_spec=__version__,
    )
    app["dao"] = Dao(
        connector=partial(aiosqlite.connect, db or BASE_DIR / "db.sqlite3")
    )
    return app


class WebServer(mode.Service):
    def __init__(self, host, port, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port: int = port

    async def on_started(self) -> None:
        await self.runner.app["dao"].create_table()

    async def on_stop(self) -> None:
        if self.runner:
            self.logger.info("web server is shutting down ...")
            await self.runner.cleanup()
        await super().on_stop()

    @mode.Service.task
    async def _serve(self):
        await self.run_app()

    @cached_property
    def runner(self):
        app = make_app()
        runner = web.AppRunner(app, logger=self.logger)
        return runner

    async def run_app(self):
        # https://docs.aiohttp.org/en/stable/web_advanced.html#application-runners
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        while not self.should_stop:
            await asyncio.sleep(3600)  # sleep forever

# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
from functools import cached_property
from asyncio import Queue

import mode

from api.server import WebServer


class Notifier(mode.Service):

    server: WebServer = WebServer()

    def __init__(self):
        super().__init__()
        self.unprocessed = Queue()

    async def on_start(self) -> None:
        await self.add_runtime_dependency(self.server)

    async def acquire(self, payload, **kwargs):
        await self.unprocessed.put(payload)

    @mode.Service.task
    async def _notify(self, **kwargs):
        pass

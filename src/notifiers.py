# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
from functools import cached_property
from asyncio import Queue

import mode
import asyncio

from src.api.server import WebServer


class Notifier(mode.Service):

    server: WebServer = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unprocessed = Queue()

    async def on_start(self) -> None:
        await self.add_runtime_dependency(self.server)

    async def acquire(self, payload, **kwargs):
        await self.unprocessed.put(payload)

    @cached_property
    def server(self):
        return WebServer()

    @mode.Service.task
    async def _notify(self, **kwargs):
        ...

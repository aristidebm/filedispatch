# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
from functools import cached_property
from asyncio import Queue

import mode


class Notifier(mode.Service):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unprocessed = Queue()

    async def acquire(self, payload, **kwargs):
        await self.unprocessed.put(payload)

    @mode.Service.task
    async def _notify(self, **kwargs):
        # TODO: How To fetch
        ...

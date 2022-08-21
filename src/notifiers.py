# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
import asyncio
from functools import cached_property
from asyncio import Queue

import mode


class Notifier(mode.Service):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unprocessed = Queue()

    def acquire(self, payload, **kwargs):
        asyncio.create_task(self.unprocessed.put(payload))

    @mode.Service.task
    async def _notify(self, **kwargs):
        # TODO: Seperate Queue consumption from processisng, so that we can use asyncio.create_task to schedule
        #  tasks for execution instead waiting them to be completed before mooving.
        ...

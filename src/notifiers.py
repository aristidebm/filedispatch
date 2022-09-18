# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
import asyncio
from functools import cached_property
from asyncio import Queue

from aiohttp import ClientError
from aiohttp_retry import RetryClient

import mode

from .utils import JSON_CONTENT_TYPE


class Notifier(mode.Service):
    async def on_start(self) -> None:
        self.unprocessed = Queue()

    def acquire(self, payload, **kwargs):
        asyncio.create_task(self.unprocessed.put(payload))

    @mode.Service.task
    async def _notify(self, **kwargs):
        while not self.should_stop:
            payload = await self.unprocessed.get()
            asyncio.create_task(self._send(payload, **kwargs))
            await self.sleep(1.0)

    async def _send(self, payload, **kwargs):
        async with RetryClient(
            raise_for_status=True, headers={"content-type": JSON_CONTENT_TYPE}
        ) as client:
            app_url = ""  # FIXME: Find a way to get the app url here.
            try:
                await client.post(app_url, data=payload)
            except ClientError as exp:
                self.logger.debug(exp)

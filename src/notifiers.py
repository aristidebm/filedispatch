# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
import asyncio
import json
from functools import cached_property
from asyncio import Queue

from aiohttp import ClientError
from aiohttp_retry import RetryClient

import mode

from .utils import JSON_CONTENT_TYPE


class Notifier(mode.Service):
    def __init__(
        self,
        host: str,
        port: int,
        path="/api/v1/logs",
        scheme: str = "http",
        *args,
        **kwargs,
    ):
        host = host and host.strip("/")
        path = path.strip("/")
        self.url = f"{scheme}://{host}:{port}/{path}"
        self.unprocessed: Queue | None = None
        super().__init__(*args, **kwargs)

    async def on_start(self) -> None:
        self.unprocessed = Queue()
        await super().on_start()

    def acquire(self, payload, **kwargs):
        asyncio.create_task(self.unprocessed.put(payload))

    @mode.Service.task
    async def _notify(self, **kwargs):
        while not self.should_stop:
            payload = await self.unprocessed.get()
            asyncio.create_task(self.notify(payload, **kwargs))
            await self.sleep(1.0)

    async def notify(self, payload, **kwargs):
        async with RetryClient() as client:
            try:
                await self._handle_notification(client, payload)
            except ClientError as exp:
                self.logger.error(exp)
                self.logger.debug(exp, stack_info=True)
                return

    async def _handle_notification(self, client, payload):
        async with client.post(self.url) as response:
            self.logger.debug(f"\n{json.dumps(payload, indent=2)}")
            if not response.ok:
                await self._handle_failure(response)

    async def _handle_failure(self, response):
        reason = await response.text()
        reason = f"{response.status} {response.reason}\n\n{reason}"
        self.logger.debug(reason)

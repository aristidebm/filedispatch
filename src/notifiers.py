# Sender Notification to the API

# This must be a service, notify method put payload in a queue, and a background task send informations to the API.
import asyncio
import json
from asyncio import Queue

import mode
from aiohttp import ClientError
from aiohttp_retry import RetryClient


class Notifier(mode.Service):
    def __init__(
        self,
        url,
        *args,
        **kwargs,
    ):
        self.url = url
        self.unprocessed: Queue[dict] = Queue()
        super().__init__(*args, **kwargs)

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
        async with client.post(self.url, json=payload) as response:
            self.logger.debug(f"\n{json.dumps(payload, indent=2)}")
            if not response.ok:
                await self._handle_failure(response)

    async def _handle_failure(self, response):
        reason = await response.text()
        reason = f"{response.status} {response.reason}\n\n{reason}"
        self.logger.debug(reason)

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
        super(Notifier, self).__init__(*args, **kwargs)
        host = host and host.strip("/")
        path = path.strip("/")
        self.url = f"{scheme}://{host}:{port}/{path}"

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
            try:
                async with client.post(self.url, data=payload) as response:
                    if response.ok:
                        self.logger.debug(
                            f"Payload {json.dumps(payload, indent=2)} is sent to the web"
                        )
                    else:
                        self.logger.debug(
                            f"Cannot send the payload {json.dumps(payload, indent=2)} to the server."
                        )
            except ClientError as exp:
                self.logger.debug(exp)
                return

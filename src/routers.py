from __future__ import annotations
import logging


from .utils import Message, get_protocol
from .workers import BaseWorker

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, workers: dict[str, BaseWorker] | None = None):
        self._workers = workers or {}

    async def route(self, msg: Message):
        raise NotImplementedError


class DefaultRouter(Router):
    async def route(self, msg: Message):
        worker = self._get_worker(msg)
        if not worker:
            return
        await worker.maybe_start()
        worker.acquire(msg)

    def _get_worker(self, msg: Message) -> BaseWorker | None:
        destination = msg.body.get("destination")
        if not destination:
            return
        key = get_protocol(destination)
        return self._workers.get(key)

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class PubSub:
    def __init__(self, queue_maxsize: int = 100) -> None:
        self._subscribers: set[asyncio.Queue[Any]] = set()
        self._queue_maxsize = queue_maxsize

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[Any]]:
        q: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_maxsize)
        self._subscribers.add(q)
        try:
            yield q
        finally:
            self._subscribers.discard(q)

    async def publish(self, event: dict) -> None:
        # Best-effort fan-out. If a queue is full, drop the event for that subscriber
        # (preserves liveness for other subscribers).
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                continue


# Module-level singleton — single-worker assumption means one bus per process.
bus = PubSub()

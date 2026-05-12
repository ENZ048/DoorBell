from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..pubsub import bus

router = APIRouter(tags=["stream"])

HEARTBEAT_INTERVAL = 15.0  # seconds


async def _event_stream():
    """SSE generator. Yields events from the pubsub bus and periodic heartbeats."""
    async with bus.subscribe() as queue:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                yield (
                    "event: heartbeat\n"
                    f"data: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"
                )
                continue
            event_name = msg.pop("event", "message")
            payload = json.dumps(msg, default=str)
            yield f"event: {event_name}\ndata: {payload}\n\n"


@router.get("/stream")
async def stream():
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

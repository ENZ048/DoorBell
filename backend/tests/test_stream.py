import asyncio
import json

import pytest

from app.pubsub import bus


async def test_stream_delivers_published_events(client):
    async def publish_after_delay():
        await asyncio.sleep(0.2)
        await bus.publish({"event": "order.updated", "snapshot": {"order_id": "X"}})

    task = asyncio.create_task(publish_after_delay())
    received: list[str] = []
    async with client.stream("GET", "/stream") as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            received.append(line)
            joined = "\n".join(received)
            if 'order.updated' in joined and 'X' in joined:
                break
    await task
    text = "\n".join(received)
    assert "event: order.updated" in text
    assert '"order_id": "X"' in text or '"order_id":"X"' in text


async def test_stream_sends_heartbeats(client, monkeypatch):
    from app.routers import stream as stream_module
    monkeypatch.setattr(stream_module, "HEARTBEAT_INTERVAL", 0.1)
    received: list[str] = []
    async with client.stream("GET", "/stream") as resp:
        async for line in resp.aiter_lines():
            received.append(line)
            if "heartbeat" in "\n".join(received):
                break
    assert any("heartbeat" in line for line in received)

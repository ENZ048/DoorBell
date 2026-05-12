import asyncio

from app.pubsub import PubSub


async def test_subscriber_receives_published_event():
    bus = PubSub()
    async with bus.subscribe() as queue:
        await bus.publish({"event": "order.updated", "id": "x"})
        msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert msg == {"event": "order.updated", "id": "x"}


async def test_multiple_subscribers_receive_same_event():
    bus = PubSub()
    async with bus.subscribe() as q1, bus.subscribe() as q2:
        await bus.publish({"event": "a"})
        m1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        m2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert m1 == {"event": "a"}
    assert m2 == {"event": "a"}


async def test_unsubscribe_on_exit():
    bus = PubSub()
    async with bus.subscribe():
        assert len(bus._subscribers) == 1
    assert len(bus._subscribers) == 0


async def test_publish_with_no_subscribers_is_noop():
    bus = PubSub()
    await bus.publish({"event": "lonely"})  # must not raise

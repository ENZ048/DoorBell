from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from . import db


async def sweep_stuck_dialing(threshold_minutes: int = 5) -> int:
    """Mark orders stuck in dialing for >threshold minutes as failed. Returns count."""
    cutoff = datetime.now(UTC) - timedelta(minutes=threshold_minutes)
    cursor = db.orders().find(
        {"call_status": "dialing", "updated_at": {"$lt": cutoff}}
    )
    stuck = await cursor.to_list(length=100)
    if not stuck:
        return 0
    ids = [d["_id"] for d in stuck]
    now = datetime.now(UTC)
    await db.orders().update_many(
        {"_id": {"$in": ids}},
        {"$set": {"call_status": "failed", "updated_at": now}},
    )
    for d in stuck:
        await db.call_events().insert_one(
            {"order_id": d["_id"], "type": "error", "source": "api",
             "payload": {"reason": "dialing timeout"}, "ts": now},
        )
    return len(stuck)


async def run_periodic(interval_seconds: int = 60) -> None:
    """Long-running task: sweeps every `interval_seconds`."""
    while True:
        try:
            await sweep_stuck_dialing()
        except Exception as e:
            import logging
            logging.warning("sweeper iteration failed: %s", e)
        await asyncio.sleep(interval_seconds)

import uuid
from datetime import datetime, timezone

import pytest


def _doc(call_status: str, bucket: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "order_id": str(uuid.uuid4()), "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 100,
        "call_status": call_status, "bucket": bucket, "action_state": None,
        "bolna_call_id": str(uuid.uuid4()), "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


async def test_stats_zero_when_empty(client):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["called"] == 0
    assert data["confirmed_count"] == 0
    assert data["issues_caught"] == 0
    assert data["cost_saved"] == 0


async def test_stats_counts_correctly(client, mock_db):
    await mock_db["orders"].insert_many([
        _doc("completed", "confirmed"),
        _doc("completed", "address_updated"),
        _doc("completed", "rescheduled"),
        _doc("completed", "cancel_intent"),
        _doc("completed", "escalate"),
        _doc("pending"),
    ])
    resp = await client.get("/api/stats")
    data = resp.json()
    assert data["called"] == 5
    assert data["confirmed_count"] == 1
    assert data["issues_caught"] == 3
    # 1.0*1 + 0.6*1 + 0.4*1 = 2.0 → cost_saved = round(2.0*100) = 200
    assert data["cost_saved"] == 200
    assert data["call_spend"] == 40  # 5 * 8
    assert data["net"] == 160

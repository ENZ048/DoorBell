from datetime import datetime, timezone

import pytest


def _doc(bucket: str | None = None, action_state: str | None = None):
    now = datetime.now(timezone.utc)
    return {
        "order_id": "SNT-1", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "call_status": "completed", "bucket": bucket, "action_state": action_state,
        "bolna_call_id": "x", "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


async def test_approve_dispatch_on_confirmed(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="confirmed"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "approve_dispatch", "note": "go"},
    )
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"_id": res.inserted_id})
    assert doc["action_state"] == "dispatched"
    assert len(doc["actions"]) == 1
    assert doc["actions"][0]["action"] == "approve_dispatch"


async def test_push_new_address_requires_address_updated_bucket(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="confirmed"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "push_new_address"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_ACTION_FOR_BUCKET"


async def test_push_new_address_on_address_updated(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="address_updated"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "push_new_address"},
    )
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"_id": res.inserted_id})
    assert doc["action_state"] == "address_pushed"


async def test_unknown_action_rejected(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="confirmed"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "made_up"},
    )
    assert resp.status_code == 422

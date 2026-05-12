from datetime import UTC, datetime

from app.config import settings


def _doc(call_id: str | None = "bx") -> dict:
    now = datetime.now(UTC)
    return {
        "order_id": "X", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "call_status": "pending", "bucket": None, "action_state": None,
        "bolna_call_id": call_id, "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


async def test_simulate_outcome_requires_admin_token(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc())
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/simulate-outcome",
        json={"bucket": "confirmed"},
    )
    assert resp.status_code == 401


async def test_simulate_outcome_address_updated(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    res = await mock_db["orders"].insert_one(_doc())
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/simulate-outcome",
        json={
            "bucket": "address_updated",
            "updated_address": "A-12, Koramangala 6th Block, BLR 560095",
        },
        headers={"X-Admin-Token": "secret"},
    )
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"_id": res.inserted_id})
    assert doc["bucket"] == "address_updated"
    assert doc["call_status"] == "completed"
    assert "Koramangala" in doc["updated_address"]
    assert len(doc["transcript"]) > 0


async def test_reset_clears_orders_and_events(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    import uuid
    await mock_db["orders"].insert_many([_doc(str(uuid.uuid4())), _doc(str(uuid.uuid4()))])
    await mock_db["call_events"].insert_one({"order_id": "x", "type": "t", "source": "s", "payload": {}, "ts": datetime.now(UTC)})
    resp = await client.post("/api/orders/reset", headers={"X-Admin-Token": "secret"})
    assert resp.status_code == 200
    assert (await mock_db["orders"].count_documents({})) == 0
    assert (await mock_db["call_events"].count_documents({})) == 0

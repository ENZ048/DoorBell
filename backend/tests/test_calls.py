from datetime import UTC, datetime

import httpx


def _base_order(order_id: str) -> dict:
    now = datetime.now(UTC)
    return {
        "order_id": order_id,
        "customer_name": "Ananya",
        "customer_phone": "+919876543210",
        "product": "Tee",
        "delivery_slot": "x",
        "delivery_slot_label": "kal subah",
        "address": "addr",
        "pincode": "560001",
        "payment_type": "COD",
        "amount": 1499,
        "call_status": "pending",
        "bolna_call_id": None,
        "bucket": None,
        "action_state": None,
        "transcript": [],
        "extracted_variables": {},
        "actions": [],
        "recording_url": None,
        "updated_address": None,
        "reschedule_preference": None,
        "created_at": now,
        "updated_at": now,
    }


async def test_trigger_call_marks_dialing(client, mock_db, respx_mock):
    oid = (await mock_db["orders"].insert_one(_base_order("SNT-1"))).inserted_id
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(200, json={"call_id": "bolna_xyz"})
    )
    resp = await client.post(f"/api/orders/{oid}/call")
    assert resp.status_code == 202
    body = resp.json()
    assert body["call_status"] == "dialing"
    assert body["bolna_call_id"] == "bolna_xyz"
    doc = await mock_db["orders"].find_one({"_id": oid})
    assert doc["call_status"] == "dialing"
    assert doc["bolna_call_id"] == "bolna_xyz"


async def test_trigger_call_handles_bolna_failure(client, mock_db, respx_mock):
    oid = (await mock_db["orders"].insert_one(_base_order("SNT-2"))).inserted_id
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(500, text="boom")
    )
    resp = await client.post(f"/api/orders/{oid}/call")
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "BOLNA_API_FAILED"
    doc = await mock_db["orders"].find_one({"_id": oid})
    assert doc["call_status"] == "failed"


async def test_call_batch_triggers_multiple(client, mock_db, respx_mock):
    ids = []
    for n in range(3):
        r = await mock_db["orders"].insert_one(_base_order(f"SNT-{n}"))
        ids.append(str(r.inserted_id))
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(200, json={"call_id": "bolna_id"})
    )
    resp = await client.post("/api/orders/call-batch", json={"order_ids": ids})
    assert resp.status_code == 202
    body = resp.json()
    assert len(body["triggered"]) == 3
    assert body["failed"] == []

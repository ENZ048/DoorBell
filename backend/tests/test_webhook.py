import asyncio
import hashlib
import hmac
from datetime import UTC, datetime

from app.config import settings
from app.pubsub import bus


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _base_doc(call_id: str, payment_type: str = "COD") -> dict:
    now = datetime.now(UTC)
    return {
        "order_id": "SNT-1", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": payment_type, "amount": 1499,
        "call_status": "dialing", "bolna_call_id": call_id, "bucket": None,
        "action_state": None, "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


async def test_webhook_classifies_confirmed(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_a"))
    payload = {
        "call_id": "bolna_a",
        "transcript": [{"role": "agent", "text": "Namaste..."}],
        "recording_url": "https://example.com/rec.mp3",
        "extracted_variables": {
            "identity_verified": True, "wrong_number": False,
            "address_confirmation": "yes", "availability": "yes",
            "cod_intent": "confirmed", "needs_human": False,
        },
    }
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_a"})
    assert doc["call_status"] == "completed"
    assert doc["bucket"] == "confirmed"
    assert doc["recording_url"] == "https://example.com/rec.mp3"


async def test_webhook_classifies_cancel_intent(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_b", payment_type="COD"))
    payload = {
        "call_id": "bolna_b",
        "extracted_variables": {
            "identity_verified": True, "wrong_number": False,
            "address_confirmation": "yes", "availability": "yes",
            "cod_intent": "cancel", "needs_human": False,
        },
    }
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_b"})
    assert doc["bucket"] == "cancel_intent"


async def test_webhook_idempotent_when_already_bucketed(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    doc = _base_doc("bolna_c")
    doc["bucket"] = "confirmed"
    doc["call_status"] = "completed"
    await mock_db["orders"].insert_one(doc)
    payload = {"call_id": "bolna_c", "extracted_variables": {"cod_intent": "cancel"}}
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    after = await mock_db["orders"].find_one({"bolna_call_id": "bolna_c"})
    assert after["bucket"] == "confirmed"  # unchanged


async def test_webhook_unknown_call_id_returns_200_but_logs(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    payload = {"call_id": "unknown", "extracted_variables": {}}
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    # an error event should be logged
    evs = await mock_db["call_events"].find({"type": "error"}).to_list(length=10)
    assert any("unknown" in str(e.get("payload", {})) for e in evs)


async def test_webhook_rejects_bad_signature(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "topsecret")
    await mock_db["orders"].insert_one(_base_doc("bolna_d"))
    resp = await client.post(
        "/webhook/bolna",
        json={"call_id": "bolna_d", "extracted_variables": {}},
        headers={"X-Bolna-Signature": "wrong"},
    )
    assert resp.status_code == 401


async def test_webhook_publishes_to_pubsub(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_e"))
    async with bus.subscribe() as q:
        payload = {
            "call_id": "bolna_e",
            "extracted_variables": {
                "identity_verified": True, "address_confirmation": "yes",
                "availability": "yes", "cod_intent": "confirmed",
            },
        }
        await client.post("/webhook/bolna", json=payload)
        msg = await asyncio.wait_for(q.get(), timeout=1.0)
    assert msg["event"] == "order.updated"
    assert "snapshot" in msg

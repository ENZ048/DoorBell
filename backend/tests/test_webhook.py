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
            "delivery_confirmed": "yes",
            "address_correct": "yes",
            "intent": "keep",
            "escalate_to_human": "false",
            "reschedule_slot": "",
            "updated_address": "",
            "cancel_reason": "",
            "call_summary": "Confirmed.",
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
            "delivery_confirmed": "yes",
            "address_correct": "yes",
            "intent": "cancel",
            "escalate_to_human": "false",
            "reschedule_slot": "",
            "updated_address": "",
            "cancel_reason": "customer changed mind",
            "call_summary": "Customer wants to cancel.",
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
                "delivery_confirmed": "yes",
                "address_correct": "yes",
                "intent": "keep",
                "escalate_to_human": "false",
                "reschedule_slot": "",
                "updated_address": "",
                "cancel_reason": "",
                "call_summary": "Confirmed.",
            },
        }
        await client.post("/webhook/bolna", json=payload)
        msg = await asyncio.wait_for(q.get(), timeout=1.0)
    assert msg["event"] == "order.updated"
    assert "snapshot" in msg


async def test_webhook_flattens_real_bolna_payload(client, mock_db, monkeypatch):
    """Test against the exact nested shape Bolna actually emits."""
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_real"))
    real_bolna_payload = {
        "call_id": "bolna_real",
        "transcript": [],
        "recording_url": None,
        "extracted_data": {
            "RTO": {
                "delivery_confirmed": {
                    "subjective": None,
                    "objective": "yes",
                    "confidence": 0.98,
                    "confidence_label": "High",
                    "reasoning_objective": "Customer confirmed availability.",
                    "validation": None,
                },
                "address_correct": {
                    "subjective": None,
                    "objective": "yes",
                    "confidence": 0.97,
                    "confidence_label": "High",
                },
                "intent": {
                    "subjective": None,
                    "objective": "keep",
                    "confidence": 0.98,
                    "confidence_label": "High",
                },
                "escalate_to_human": {
                    "subjective": None,
                    "objective": "false",
                    "confidence": 0.95,
                    "confidence_label": "High",
                },
                "call_summary": {
                    "subjective": "Customer confirmed delivery and address. No action needed.",
                    "objective": None,
                    "confidence": 0.95,
                    "confidence_label": "High",
                },
                "reschedule_slot": {"subjective": "", "objective": None, "confidence": 0},
                "updated_address": {"subjective": "", "objective": None, "confidence": 0},
                "cancel_reason": {"subjective": "", "objective": None, "confidence": 0},
            }
        },
    }
    resp = await client.post("/webhook/bolna", json=real_bolna_payload)
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_real"})
    assert doc["call_status"] == "completed"
    assert doc["bucket"] == "confirmed", f"expected confirmed, got {doc['bucket']}"
    # Flat extracted_variables should be on the order doc
    assert doc["extracted_variables"]["delivery_confirmed"] == "yes"
    assert doc["extracted_variables"]["intent"] == "keep"
    assert doc["extracted_variables"]["escalate_to_human"] == "false"
    assert "Customer confirmed delivery" in doc["extracted_variables"]["call_summary"]


async def test_webhook_parses_string_transcript_and_nested_recording(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_string_t"))
    payload = {
        "call_id": "bolna_string_t",
        "transcript": (
            "assistant: Namaste, kya main Ananya se baat kar rahi hoon?\n"
            "user: Haan bolo\n"
            "assistant: Address sahi hai?\n"
            "user: Haan sahi hai\n"
        ),
        "telephony_data": {
            "recording_url": "https://example.com/rec123.mp3",
        },
        "extracted_data": {
            "RTO": {
                "delivery_confirmed": {"objective": "yes", "subjective": None, "confidence": 0.9},
                "address_correct": {"objective": "yes", "subjective": None, "confidence": 0.9},
                "intent": {"objective": "keep", "subjective": None, "confidence": 0.9},
                "escalate_to_human": {"objective": "false", "subjective": None, "confidence": 0.9},
            }
        },
    }
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_string_t"})
    assert doc["bucket"] == "confirmed"
    assert len(doc["transcript"]) == 4
    assert doc["transcript"][0]["role"] == "agent"
    assert "Namaste" in doc["transcript"][0]["text"]
    assert doc["transcript"][1]["role"] == "customer"
    assert "Haan bolo" in doc["transcript"][1]["text"]
    assert doc["recording_url"] == "https://example.com/rec123.mp3"


async def test_webhook_handles_address_updated_real_payload(client, mock_db, monkeypatch):
    """Address-updated bucket via real Bolna nested payload."""
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_addr"))
    payload = {
        "call_id": "bolna_addr",
        "extracted_data": {
            "RTO": {
                "delivery_confirmed": {"objective": "yes", "subjective": None, "confidence": 0.9},
                "address_correct": {"objective": "updated", "subjective": None, "confidence": 0.95},
                "updated_address": {
                    "subjective": "A-12, Koramangala 6th Block, Bangalore 560095, near KFC",
                    "objective": None,
                    "confidence": 0.95,
                },
                "intent": {"objective": "keep", "subjective": None, "confidence": 0.9},
                "escalate_to_human": {"objective": "false", "subjective": None, "confidence": 0.9},
                "reschedule_slot": {"subjective": "", "objective": None, "confidence": 0},
                "cancel_reason": {"subjective": "", "objective": None, "confidence": 0},
                "call_summary": {
                    "subjective": "Address changed.",
                    "objective": None,
                    "confidence": 0.9,
                },
            }
        },
    }
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_addr"})
    assert doc["bucket"] == "address_updated"
    assert "Koramangala" in doc["updated_address"]

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request

from .. import db
from ..auth import verify_bolna_signature
from ..classifier import classify
from ..config import settings
from ..models import CallStatus, PaymentType
from ..pubsub import bus

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _projection(doc: dict) -> dict:
    """Minimal projection sent over SSE."""
    return {
        "_id": str(doc.get("_id")),
        "order_id": doc.get("order_id"),
        "call_status": doc.get("call_status"),
        "bucket": doc.get("bucket"),
        "action_state": doc.get("action_state"),
        "customer_name": doc.get("customer_name"),
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


@router.post("/bolna")
async def bolna_webhook(request: Request, x_bolna_signature: str | None = Header(default=None)):
    raw = await request.body()
    secret = settings.bolna_webhook_secret
    if secret:
        if not verify_bolna_signature(raw, x_bolna_signature, secret):
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "BAD_SIGNATURE", "message": "HMAC verification failed"}},
            )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_JSON", "message": "invalid JSON"}},
        ) from exc

    call_id = payload.get("call_id") or payload.get("callId") or payload.get("id")
    if not call_id:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "MISSING_CALL_ID", "message": "call_id required"}},
        )

    now = datetime.now(UTC)
    doc = await db.orders().find_one({"bolna_call_id": call_id})
    if not doc:
        await db.call_events().insert_one(
            {"order_id": None, "type": "error", "source": "bolna",
             "payload": {"reason": "unknown call_id", "call_id": call_id}, "ts": now},
        )
        return {"ok": True}

    # Idempotency: don't re-bucket if already classified
    if doc.get("bucket"):
        await db.call_events().insert_one(
            {"order_id": doc["_id"], "type": "webhook_received", "source": "bolna",
             "payload": {"duplicate": True, "raw": payload}, "ts": now},
        )
        return {"ok": True}

    extracted = payload.get("extracted_variables", {}) or {}
    transcript = payload.get("transcript", []) or []
    recording_url = payload.get("recording_url")
    payment_type = PaymentType(doc.get("payment_type", "PREPAID"))
    bucket = classify(extracted, payment_type)

    update_fields = {
        "call_status": CallStatus.COMPLETED.value,
        "bucket": bucket.value,
        "transcript": transcript,
        "recording_url": recording_url,
        "extracted_variables": extracted,
        "updated_address": extracted.get("updated_address"),
        "reschedule_preference": extracted.get("reschedule_preference"),
        "updated_at": now,
    }

    await db.orders().update_one({"_id": doc["_id"]}, {"$set": update_fields})

    await db.call_events().insert_one(
        {"order_id": doc["_id"], "type": "webhook_received", "source": "bolna",
         "payload": payload, "ts": now},
    )
    await db.call_events().insert_one(
        {"order_id": doc["_id"], "type": "bucketed", "source": "bolna",
         "payload": {"bucket": bucket.value}, "ts": now},
    )

    fresh = await db.orders().find_one({"_id": doc["_id"]})
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})

    return {"ok": True}

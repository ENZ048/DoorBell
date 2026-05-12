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


def _flatten_bolna_extracted(payload: dict) -> dict:
    """
    Flatten Bolna's nested extraction payload into a flat dict of field -> value.

    Bolna's structured output looks like:
      payload["extracted_data"]["<CategoryName>"]["<field>"] = {
        "subjective": <free_text_or_empty>,
        "objective": <pre_defined_value_or_None>,
        "confidence": float,
        ...
      }

    We flatten to: {"<field>": "value", ...} where value = objective if non-None,
    else subjective if non-empty, else None.

    Also accepts already-flat payloads for resilience:
      payload["extracted_variables"]["<field>"] = "value"  (flat fallback)
    """
    src = payload.get("extracted_data") or payload.get("extracted_variables") or {}
    flat: dict = {}

    def _extract_field_value(field_obj):
        """Given a Bolna per-field object with subjective/objective, return the meaningful value."""
        if not isinstance(field_obj, dict):
            return field_obj
        # Bolna shape: prefer objective (pre-defined), fall back to subjective (free text)
        obj = field_obj.get("objective")
        if obj is not None and obj != "":
            return obj
        subj = field_obj.get("subjective")
        if subj is not None and subj != "":
            return subj
        return None

    if not isinstance(src, dict):
        return {}

    # Detect whether src is category-nested or already flat
    sample_value = next(iter(src.values()), None)
    is_category_nested = isinstance(sample_value, dict) and any(
        isinstance(v, dict) and ("objective" in v or "subjective" in v)
        for v in sample_value.values()
        if isinstance(v, dict)
    )

    if is_category_nested:
        for _category_name, category_value in src.items():
            if not isinstance(category_value, dict):
                continue
            for field_name, field_value in category_value.items():
                flat[field_name] = _extract_field_value(field_value)
    else:
        # Flat shape OR per-field-only nested (no category wrapper)
        for field_name, field_value in src.items():
            if isinstance(field_value, dict) and (
                "objective" in field_value or "subjective" in field_value
            ):
                flat[field_name] = _extract_field_value(field_value)
            else:
                flat[field_name] = field_value

    return flat


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

    extracted = _flatten_bolna_extracted(payload)
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
        "reschedule_preference": extracted.get("reschedule_slot"),
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

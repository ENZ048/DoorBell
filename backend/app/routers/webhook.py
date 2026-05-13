from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request

from .. import db
from ..auth import verify_bolna_signature
from ..classifier import classify
from ..config import settings
from ..models import CallStatus, PaymentType
from ..pubsub import bus

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _parse_transcript(raw) -> list[dict]:
    """
    Bolna sends transcript as a multi-line string with role prefixes like:
        "assistant: Namaste...
         user: Haan bolo
         assistant: ..."
    Convert to list[{role, speaker_label, text}]. If `raw` is already a list,
    pass through. If empty/None, return [].
    """
    if not raw:
        return []
    if isinstance(raw, list):
        # Already structured
        return raw
    if not isinstance(raw, str):
        return []
    turns: list[dict] = []
    # Pattern: capture role at line start, then text up to the next role or end.
    pattern = re.compile(
        r"^(assistant|user)\s*:\s*(.*?)(?=^(?:assistant|user)\s*:|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    for match in pattern.finditer(raw):
        role_raw, text = match.group(1), match.group(2).strip()
        if not text:
            continue
        role = "agent" if role_raw == "assistant" else "customer"
        turns.append({"role": role, "speaker_label": "", "text": text})
    # Fallback: if no matches and we have content, store as a single agent turn so it shows.
    if not turns and raw.strip():
        turns.append({"role": "agent", "speaker_label": "", "text": raw.strip()})
    return turns


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

    # Skip non-terminal webhook events (e.g. status="initiated") that carry no
    # extracted_data — classifying an empty dict always falls through to ESCALATE.
    call_status = payload.get("status", "")
    if call_status and call_status not in {"completed", "error", "rejected", "cancelled"}:
        await db.call_events().insert_one(
            {"order_id": doc["_id"], "type": "webhook_received", "source": "bolna",
             "payload": payload, "ts": now},
        )
        return {"ok": True}

    extracted = _flatten_bolna_extracted(payload)
    transcript = _parse_transcript(payload.get("transcript"))
    recording_url = (
        payload.get("recording_url")
        or (payload.get("telephony_data") or {}).get("recording_url")
    )

    # ---- No-answer / unreachable detection ----
    # If Bolna's telephony layer reports the customer didn't pick up (no_answer,
    # busy, voicemail, machine_detection, originate_failed, etc.), we record the
    # call as `no_answer` and SKIP bucket classification. Calling escalate on an
    # empty extracted_data is misleading — nothing to escalate, nobody talked.
    hangup_reason_raw = (payload.get("telephony_data") or {}).get("hangup_reason") or ""
    hangup_reason = str(hangup_reason_raw).lower()
    # Substring match keeps us robust to provider-specific wording
    # (e.g. "no_answer", "call_not_answered", "user_busy", "voicemail_machine").
    NO_ANSWER_NEEDLES = (
        "no_answer", "no-answer", "not_answered", "not-answered",
        "busy", "voicemail", "machine_detection", "answered_by_machine",
        "originate_fail", "rejected", "unreachable", "cancelled_by_caller",
    )
    is_no_answer = any(needle in hangup_reason for needle in NO_ANSWER_NEEDLES)
    # Also infer no_answer when extracted_data is completely empty AND we have
    # no transcript turns — sometimes Bolna doesn't set hangup_reason explicitly.
    if not is_no_answer and not extracted and len(transcript) == 0:
        is_no_answer = True

    if is_no_answer:
        await db.orders().update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "call_status": CallStatus.NO_ANSWER.value,
                "transcript": transcript,
                "recording_url": recording_url,
                "extracted_variables": extracted,
                "updated_at": now,
            }},
        )
        await db.call_events().insert_one(
            {"order_id": doc["_id"], "type": "webhook_received", "source": "bolna",
             "payload": payload, "ts": now},
        )
        await db.call_events().insert_one(
            {"order_id": doc["_id"], "type": "no_answer", "source": "bolna",
             "payload": {"hangup_reason": hangup_reason_raw}, "ts": now},
        )
        fresh = await db.orders().find_one({"_id": doc["_id"]})
        await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})
        return {"ok": True}

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

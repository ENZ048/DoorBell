from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .. import db
from ..auth import require_admin_token
from ..config import settings
from ..models import Bucket
from ..pubsub import bus
from ..routers.webhook import _projection

router = APIRouter(prefix="/api/orders", tags=["demo"])


SYNTHETIC_TRANSCRIPTS = {
    "confirmed": [
        {"role": "agent", "text": "Namaste, kya main aapse baat kar rahi hoon?"},
        {"role": "customer", "text": "Haan, bolo."},
        {"role": "agent", "text": "Address aur slot confirm hai?"},
        {"role": "customer", "text": "Haan bilkul, deliver kar do."},
    ],
    "address_updated": [
        {"role": "agent", "text": "Address sahi hai ya kuch change?"},
        {"role": "customer",
         "text": "Sorry main bhai ke ghar shift ho gaya hoon, naya address bolta hoon."},
    ],
    "rescheduled": [
        {"role": "agent", "text": "Kal slot mein ghar par honge?"},
        {"role": "customer", "text": "Kal nahi, parso subah convenient hai."},
    ],
    "cancel_intent": [
        {"role": "agent", "text": "COD amount ready rakhenge?"},
        {"role": "customer", "text": "Actually mujhe yeh order cancel karna hai."},
    ],
    "escalate": [
        {"role": "agent", "text": "Confirm karein..."},
        {"role": "customer", "text": "Mujhe team se baat karni hai."},
    ],
}


class SimulateRequest(BaseModel):
    bucket: str
    updated_address: str | None = None
    reschedule_preference: str | None = None


@router.post("/reset")
async def reset_all(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    require_admin_token(x_admin_token, settings.admin_token)
    await db.orders().delete_many({})
    await db.call_events().delete_many({})
    await bus.publish({"event": "orders.reset"})
    return {"ok": True}


@router.post("/{order_id}/simulate-outcome")
async def simulate_outcome(
    order_id: str,
    req: SimulateRequest,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    require_admin_token(x_admin_token, settings.admin_token)
    if req.bucket not in {b.value for b in Bucket}:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNKNOWN_BUCKET", "message": req.bucket}},
        )
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "invalid id"}},
        )
    doc = await db.orders().find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "order not found"}},
        )

    now = datetime.now(timezone.utc)
    extracted = {
        "identity_verified": True,
        "wrong_number": False,
        "address_confirmation": "updated" if req.bucket == "address_updated" else "yes",
        "availability": "reschedule" if req.bucket == "rescheduled" else "yes",
        "cod_intent": (
            "cancel" if req.bucket == "cancel_intent"
            else ("confirmed" if doc.get("payment_type") == "COD" else "na")
        ),
        "needs_human": req.bucket == "escalate",
        "updated_address": req.updated_address,
        "reschedule_preference": req.reschedule_preference,
    }
    transcript = SYNTHETIC_TRANSCRIPTS.get(req.bucket, [])
    await db.orders().update_one(
        {"_id": oid},
        {"$set": {
            "call_status": "completed",
            "bucket": req.bucket,
            "transcript": transcript,
            "extracted_variables": extracted,
            "updated_address": req.updated_address,
            "reschedule_preference": req.reschedule_preference,
            "updated_at": now,
        }},
    )
    await db.call_events().insert_one(
        {"order_id": oid, "type": "bucketed", "source": "seller",
         "payload": {"simulated": True, "bucket": req.bucket}, "ts": now},
    )
    fresh = await db.orders().find_one({"_id": oid})
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})
    return {"ok": True, "order_id": str(oid), "bucket": req.bucket}

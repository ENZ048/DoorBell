from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..pubsub import bus
from ..routers.webhook import _projection

router = APIRouter(prefix="/api/orders", tags=["actions"])

# Map action → derived action_state, and which buckets each action is valid for
ACTION_MAP: dict[str, tuple[str, set[str]]] = {
    "approve_dispatch": (
        "dispatched",
        {"confirmed", "address_updated", "rescheduled", "escalate"},
    ),
    "cancel_dispatch": (
        "cancelled",
        {"confirmed", "address_updated", "rescheduled", "cancel_intent", "escalate",
         "no_answer", "failed"},
    ),
    "push_new_address": ("address_pushed", {"address_updated"}),
    "confirm_reschedule": ("rescheduled_confirmed", {"rescheduled"}),
    "assign_human": (
        "human_assigned",
        {"escalate", "cancel_intent", "confirmed", "address_updated", "rescheduled",
         "no_answer", "failed"},
    ),
}


class ActionRequest(BaseModel):
    action: str
    note: str | None = None


@router.post("/{order_id}/action")
async def record_action(order_id: str, req: ActionRequest):
    if req.action not in ACTION_MAP:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNKNOWN_ACTION", "message": f"unknown action {req.action}"}},
        )
    action_state, valid_buckets = ACTION_MAP[req.action]
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

    current_bucket = doc.get("bucket") or doc.get("call_status")  # allow no_answer/failed
    if current_bucket not in valid_buckets:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_ACTION_FOR_BUCKET",
                              "message": f"action {req.action} not valid for {current_bucket}"}},
        )

    now = datetime.now(timezone.utc)
    action_entry = {"action": req.action, "note": req.note, "by": "seller", "ts": now}
    await db.orders().update_one(
        {"_id": oid},
        {
            "$push": {"actions": action_entry},
            "$set": {"action_state": action_state, "updated_at": now},
        },
    )
    await db.call_events().insert_one(
        {"order_id": oid, "type": "action_taken", "source": "seller",
         "payload": action_entry, "ts": now},
    )
    fresh = await db.orders().find_one({"_id": oid})
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})

    from .orders import _serialize
    return {"order": _serialize(fresh)}

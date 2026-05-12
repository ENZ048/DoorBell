from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from .. import db
from ..bolna import BolnaClient, BolnaError
from ..config import settings

router = APIRouter(prefix="/api/orders", tags=["calls"])


class BatchRequest(BaseModel):
    order_ids: list[str] | None = None
    all_pending: bool = False


def _bolna_client() -> BolnaClient:
    return BolnaClient(api_key=settings.bolna_api_key, base_url=settings.bolna_base_url)


def _webhook_url() -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/webhook/bolna"


def _variables(doc: dict, brand_name: str = "Snitch") -> dict:
    addr = doc.get("address", "")
    address_short = addr.split(",")[0] if "," in addr else addr
    return {
        "customer_name": doc.get("customer_name", ""),
        "brand_name": brand_name,
        "order_id": doc.get("order_id", ""),
        "product": doc.get("product", ""),
        "delivery_slot_label": doc.get("delivery_slot_label", ""),
        "address_short": address_short,
        "payment_type": doc.get("payment_type", ""),
        "amount": doc.get("amount", 0),
    }


async def _dispatch_one(order_id: ObjectId, doc: dict) -> dict:
    now = datetime.now(timezone.utc)
    client = _bolna_client()
    try:
        call_id = await client.create_call(
            agent_id=settings.bolna_agent_id,
            recipient_phone=doc["customer_phone"],
            variables=_variables(doc),
            webhook_url=_webhook_url(),
        )
    except BolnaError as e:
        await db.orders().update_one(
            {"_id": order_id},
            {"$set": {"call_status": "failed", "updated_at": now}},
        )
        await db.call_events().insert_one(
            {"order_id": order_id, "type": "error", "source": "bolna",
             "payload": {"message": str(e)}, "ts": now},
        )
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "BOLNA_API_FAILED", "message": str(e)}},
        )
    try:
        await db.orders().update_one(
            {"_id": order_id},
            {"$set": {"call_status": "dialing", "bolna_call_id": call_id, "updated_at": now}},
        )
    except DuplicateKeyError:
        # Unique index on bolna_call_id — call was already recorded; treat as success.
        pass
    await db.call_events().insert_one(
        {"order_id": order_id, "type": "call_initiated", "source": "api",
         "payload": {"bolna_call_id": call_id}, "ts": now},
    )
    fresh = await db.orders().find_one({"_id": order_id})
    from ..pubsub import bus
    from ..routers.webhook import _projection
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})
    return {"call_status": "dialing", "bolna_call_id": call_id}


@router.post("/call-batch", status_code=202)
async def trigger_batch(req: BatchRequest):
    if req.all_pending:
        cursor = db.orders().find({"call_status": "pending"}).limit(100)
        docs = await cursor.to_list(length=100)
    else:
        if not req.order_ids:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "INVALID_REQUEST",
                                  "message": "order_ids required when all_pending=false"}},
            )
        oids = [ObjectId(x) for x in req.order_ids]
        cursor = db.orders().find({"_id": {"$in": oids}})
        docs = await cursor.to_list(length=len(oids))

    sem = asyncio.Semaphore(3)
    triggered: list[dict] = []
    failed: list[dict] = []

    async def _safe(doc):
        async with sem:
            try:
                res = await _dispatch_one(doc["_id"], doc)
                triggered.append({"order_id": str(doc["_id"]), **res})
            except HTTPException as e:
                failed.append({"order_id": str(doc["_id"]), "error": e.detail})

    await asyncio.gather(*[_safe(d) for d in docs])
    return {"triggered": triggered, "failed": failed}


@router.post("/{order_id}/call", status_code=202)
async def trigger_call(order_id: str):
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
    result = await _dispatch_one(oid, doc)
    return result

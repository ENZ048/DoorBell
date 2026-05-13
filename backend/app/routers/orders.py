from __future__ import annotations

from datetime import UTC, datetime

import httpx
from bson import ObjectId
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from .. import db
from ..csv_parser import parse_csv

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _serialize(doc: dict) -> dict:
    """Convert Mongo doc to JSON-safe dict (ObjectId/datetime → strings)."""
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for k, v in out.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


@router.post("/upload")
async def upload_orders(file: UploadFile):
    body = await file.read()
    try:
        result = parse_csv(body)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_CSV", "message": str(e)}},
        ) from e
    inserted_serialized: list[dict] = []
    now = datetime.now(UTC)
    for order in result.inserted:
        doc = order.model_dump(mode="json")
        # Ensure proper datetime objects in Mongo (not strings)
        doc["created_at"] = now
        doc["updated_at"] = now
        insert_res = await db.orders().insert_one(doc)
        doc["_id"] = insert_res.inserted_id
        inserted_serialized.append(_serialize(doc))
        await db.call_events().insert_one(
            {
                "order_id": insert_res.inserted_id,
                "type": "created",
                "source": "csv",
                "payload": {"order_id_external": order.order_id},
                "ts": now,
            }
        )
    return {
        "total_parsed": result.total_parsed,
        "inserted": inserted_serialized,
        "rejected": [
            {"row_number": r.row_number, "raw": r.raw, "reason": r.reason}
            for r in result.rejected
        ],
    }


@router.get("")
async def list_orders(
    call_status: str | None = None,
    bucket: str | None = None,
    action_state: str | None = None,
    limit: int = 100,
):
    query: dict = {}
    if call_status:
        query["call_status"] = call_status
    if bucket:
        query["bucket"] = bucket
    if action_state:
        query["action_state"] = action_state
    cursor = db.orders().find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"orders": [_serialize(d) for d in docs], "next_cursor": None}


@router.get("/{order_id}")
async def get_order(order_id: str):
    try:
        oid = ObjectId(order_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": f"invalid id {order_id}"}},
        ) from exc
    doc = await db.orders().find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "order not found"}},
        )
    events_cursor = db.call_events().find({"order_id": oid}).sort("ts", 1).limit(20)
    events = await events_cursor.to_list(length=20)
    serialized_events = []
    for e in events:
        ev = dict(e)
        ev["_id"] = str(ev["_id"])
        ev["order_id"] = str(ev["order_id"])
        if isinstance(ev.get("ts"), datetime):
            ev["ts"] = ev["ts"].isoformat()
        serialized_events.append(ev)
    out = _serialize(doc)
    out["events"] = serialized_events
    return out


@router.get("/{order_id}/recording")
async def download_recording(order_id: str):
    """Proxy the Bolna recording with a Content-Disposition: attachment header
    so the browser downloads it instead of opening in a tab. Cross-origin
    `download` attributes on the S3 URL get ignored by browsers, so we stream
    through our own origin and set the right headers ourselves."""
    try:
        oid = ObjectId(order_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "invalid id"}},
        ) from exc
    doc = await db.orders().find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "order not found"}},
        )
    url = doc.get("recording_url")
    if not url:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NO_RECORDING", "message": "no recording for this order"}},
        )

    filename = f"doorbell-{doc.get('order_id', order_id)}.mp3"
    client = httpx.AsyncClient(timeout=30.0)

    async def stream():
        try:
            async with client.stream("GET", url) as resp:
                if resp.status_code >= 400:
                    return
                async for chunk in resp.aiter_bytes(64 * 1024):
                    yield chunk
        finally:
            await client.aclose()

    return StreamingResponse(
        stream(),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )

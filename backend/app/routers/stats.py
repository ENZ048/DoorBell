from fastapi import APIRouter

from .. import db

router = APIRouter(prefix="/api", tags=["stats"])

CALL_COST = 8
RTO_COST = 100


@router.get("/stats")
async def stats() -> dict:
    pipeline = [
        {
            "$group": {
                "_id": None,
                "called": {
                    "$sum": {"$cond": [{"$eq": ["$call_status", "completed"]}, 1, 0]}
                },
                "confirmed": {
                    "$sum": {"$cond": [{"$eq": ["$bucket", "confirmed"]}, 1, 0]}
                },
                "address_updated": {
                    "$sum": {"$cond": [{"$eq": ["$bucket", "address_updated"]}, 1, 0]}
                },
                "rescheduled": {
                    "$sum": {"$cond": [{"$eq": ["$bucket", "rescheduled"]}, 1, 0]}
                },
                "cancel_intent": {
                    "$sum": {"$cond": [{"$eq": ["$bucket", "cancel_intent"]}, 1, 0]}
                },
                "escalate": {
                    "$sum": {"$cond": [{"$eq": ["$bucket", "escalate"]}, 1, 0]}
                },
            }
        }
    ]
    try:
        agg = await db.orders().aggregate(pipeline).to_list(length=1)
        if not agg:
            raise ValueError("empty")
        a = agg[0]
        called = a["called"]
        confirmed = a["confirmed"]
        addr_u = a["address_updated"]
        resched = a["rescheduled"]
        cancel = a["cancel_intent"]
        esc = a["escalate"]
    except Exception:
        # Fallback: Python-side count when aggregation operators are unsupported
        docs = await db.orders().find({}, {"call_status": 1, "bucket": 1}).to_list(length=None)
        called = sum(1 for d in docs if d.get("call_status") == "completed")
        confirmed = sum(1 for d in docs if d.get("bucket") == "confirmed")
        addr_u = sum(1 for d in docs if d.get("bucket") == "address_updated")
        resched = sum(1 for d in docs if d.get("bucket") == "rescheduled")
        cancel = sum(1 for d in docs if d.get("bucket") == "cancel_intent")
        esc = sum(1 for d in docs if d.get("bucket") == "escalate")

    issues = addr_u + resched + cancel
    saved_rto = 1.0 * cancel + 0.6 * addr_u + 0.4 * resched
    cost_saved = round(saved_rto * RTO_COST)
    call_spend = called * CALL_COST
    return {
        "called": called,
        "confirmed_count": confirmed,
        "address_updated_count": addr_u,
        "rescheduled_count": resched,
        "cancel_intent_count": cancel,
        "escalate_count": esc,
        "issues_caught": issues,
        "cost_saved": cost_saved,
        "call_spend": call_spend,
        "net": cost_saved - call_spend,
    }

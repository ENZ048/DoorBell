from datetime import UTC, datetime, timedelta

from app.sweeper import sweep_stuck_dialing


async def test_sweep_marks_stuck_dialing_as_failed(mock_db):
    now = datetime.now(UTC)
    stuck = {
        "order_id": "OLD", "call_status": "dialing", "bolna_call_id": "bx",
        "updated_at": now - timedelta(minutes=10),
        "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "bucket": None, "action_state": None, "transcript": [],
        "extracted_variables": {}, "actions": [], "recording_url": None,
        "updated_address": None, "reschedule_preference": None,
        "created_at": now - timedelta(minutes=10),
    }
    fresh = {**stuck, "order_id": "NEW", "bolna_call_id": "by", "updated_at": now}
    await mock_db["orders"].insert_many([stuck, fresh])
    n = await sweep_stuck_dialing(threshold_minutes=5)
    assert n == 1
    old = await mock_db["orders"].find_one({"order_id": "OLD"})
    assert old["call_status"] == "failed"
    new = await mock_db["orders"].find_one({"order_id": "NEW"})
    assert new["call_status"] == "dialing"

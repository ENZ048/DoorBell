from datetime import datetime

import pytest

from app.models import (
    Action,
    ActionState,
    Bucket,
    CallEvent,
    CallStatus,
    Order,
    PaymentType,
)


def test_order_defaults_are_pending():
    order = Order(
        order_id="SNT-1",
        customer_name="Ananya",
        customer_phone="+919876543210",
        product="Tee",
        delivery_slot="2026-05-12T10:00:00+05:30/2026-05-12T13:00:00+05:30",
        delivery_slot_label="kal subah 10 se 1 baje",
        address="B-204, BLR",
        pincode="560038",
        payment_type=PaymentType.COD,
        amount=1499,
    )
    assert order.call_status is CallStatus.PENDING
    assert order.bucket is None
    assert order.action_state is None
    assert order.actions == []
    assert isinstance(order.created_at, datetime)


def test_order_phone_must_be_e164():
    with pytest.raises(ValueError):
        Order(
            order_id="X",
            customer_name="A",
            customer_phone="9876543210",  # missing + prefix
            product="P",
            delivery_slot="2026-05-12T10:00:00+05:30/2026-05-12T13:00:00+05:30",
            delivery_slot_label="kal",
            address="addr",
            pincode="560038",
            payment_type=PaymentType.PREPAID,
            amount=100,
        )


def test_action_records_required_fields():
    a = Action(action="approve_dispatch", note="LGTM", by="seller@brand.com")
    assert a.action == "approve_dispatch"
    assert a.note == "LGTM"
    assert isinstance(a.ts, datetime)


def test_call_event_minimal():
    e = CallEvent(order_id="abc", type="created", source="csv", payload={})
    assert e.type == "created"
    assert isinstance(e.ts, datetime)


def test_bucket_and_action_state_enums_are_exhaustive():
    assert {b.value for b in Bucket} == {
        "confirmed",
        "address_updated",
        "rescheduled",
        "cancel_intent",
        "escalate",
    }
    assert {s.value for s in ActionState} == {
        "dispatched",
        "cancelled",
        "rescheduled_confirmed",
        "address_pushed",
        "human_assigned",
    }

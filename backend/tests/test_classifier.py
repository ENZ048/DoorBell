import pytest

from app.classifier import classify
from app.models import Bucket, PaymentType


def vars_(**overrides):
    base = {
        "delivery_confirmed": "yes",
        "address_correct": "yes",
        "intent": "keep",
        "escalate_to_human": "false",
        "reschedule_slot": "",
        "updated_address": "",
        "cancel_reason": "",
        "call_summary": "",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "extracted,payment_type,expected",
    [
        # Happy path COD
        (vars_(), PaymentType.COD, Bucket.CONFIRMED),
        # Happy path PREPAID
        (vars_(), PaymentType.PREPAID, Bucket.CONFIRMED),
        # Escalate from escalate_to_human flag
        (vars_(escalate_to_human="true"), PaymentType.COD, Bucket.ESCALATE),
        # Escalate from delivery_confirmed=no
        (vars_(delivery_confirmed="no"), PaymentType.COD, Bucket.ESCALATE),
        # Cancel intent — COD
        (vars_(intent="cancel"), PaymentType.COD, Bucket.CANCEL_INTENT),
        # Cancel intent — PREPAID (no longer COD-gated)
        (vars_(intent="cancel"), PaymentType.PREPAID, Bucket.CANCEL_INTENT),
        # Address updated
        (vars_(address_correct="updated"), PaymentType.COD, Bucket.ADDRESS_UPDATED),
        # Rescheduled via delivery_confirmed=reschedule
        (vars_(delivery_confirmed="reschedule"), PaymentType.COD, Bucket.RESCHEDULED),
        # Rescheduled via intent=reschedule
        (vars_(intent="reschedule"), PaymentType.COD, Bucket.RESCHEDULED),
        # Priority: escalate beats cancel
        (vars_(escalate_to_human="true", intent="cancel"), PaymentType.COD, Bucket.ESCALATE),
        # Priority: cancel beats address_updated
        (vars_(intent="cancel", address_correct="updated"), PaymentType.COD, Bucket.CANCEL_INTENT),
        # Priority: address beats reschedule
        (
            vars_(address_correct="updated", delivery_confirmed="reschedule"),
            PaymentType.COD,
            Bucket.ADDRESS_UPDATED,
        ),
        # Truthiness: escalate_to_human as Python bool True
        (vars_(escalate_to_human=True), PaymentType.COD, Bucket.ESCALATE),
        # Truthiness: escalate_to_human as string "True" (capital T)
        (vars_(escalate_to_human="True"), PaymentType.COD, Bucket.ESCALATE),
        # Fallback: empty dict → escalate
        ({}, PaymentType.COD, Bucket.ESCALATE),
    ],
)
def test_classify_matrix(extracted, payment_type, expected):
    assert classify(extracted, payment_type) is expected

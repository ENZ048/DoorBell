import pytest

from app.classifier import classify
from app.models import Bucket, PaymentType


def vars_(**overrides):
    base = {
        "identity_verified": True,
        "wrong_number": False,
        "address_confirmation": "yes",
        "availability": "yes",
        "cod_intent": "na",
        "needs_human": False,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "extracted,payment_type,expected",
    [
        # Happy paths
        (vars_(), PaymentType.PREPAID, Bucket.CONFIRMED),
        (vars_(cod_intent="confirmed"), PaymentType.COD, Bucket.CONFIRMED),
        # Escalate (highest priority)
        (vars_(wrong_number=True), PaymentType.PREPAID, Bucket.ESCALATE),
        (vars_(needs_human=True), PaymentType.COD, Bucket.ESCALATE),
        # Cancel intent (COD only)
        (vars_(cod_intent="cancel"), PaymentType.COD, Bucket.CANCEL_INTENT),
        # Address updated
        (vars_(address_confirmation="updated"), PaymentType.PREPAID, Bucket.ADDRESS_UPDATED),
        # Rescheduled
        (vars_(availability="reschedule"), PaymentType.PREPAID, Bucket.RESCHEDULED),
        # Priority: escalate beats cancel
        (vars_(needs_human=True, cod_intent="cancel"), PaymentType.COD, Bucket.ESCALATE),
        # Priority: cancel beats address_updated
        (
            vars_(cod_intent="cancel", address_confirmation="updated"),
            PaymentType.COD,
            Bucket.CANCEL_INTENT,
        ),
        # Priority: address beats reschedule
        (
            vars_(address_confirmation="updated", availability="reschedule"),
            PaymentType.PREPAID,
            Bucket.ADDRESS_UPDATED,
        ),
        # cod_intent=cancel on PREPAID is ignored (na expected anyway)
        (vars_(cod_intent="cancel"), PaymentType.PREPAID, Bucket.CONFIRMED),
        # Not-confirmed states fall back to escalate via incomplete classification
        (vars_(address_confirmation="not_confirmed"), PaymentType.PREPAID, Bucket.ESCALATE),
        (vars_(availability="not_confirmed"), PaymentType.PREPAID, Bucket.ESCALATE),
    ],
)
def test_classify_matrix(extracted, payment_type, expected):
    assert classify(extracted, payment_type) is expected

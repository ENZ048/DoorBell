from typing import Any

from .models import Bucket, PaymentType


def classify(extracted: dict[str, Any], payment_type: PaymentType) -> Bucket:
    """First-match-wins bucket assignment per spec §4."""
    if extracted.get("wrong_number") is True:
        return Bucket.ESCALATE
    if extracted.get("needs_human") is True:
        return Bucket.ESCALATE
    if extracted.get("error_flag") is True:
        return Bucket.ESCALATE

    if payment_type is PaymentType.COD and extracted.get("cod_intent") == "cancel":
        return Bucket.CANCEL_INTENT

    if extracted.get("address_confirmation") == "updated":
        return Bucket.ADDRESS_UPDATED

    if extracted.get("availability") == "reschedule":
        return Bucket.RESCHEDULED

    # Confirmed requires all four positive signals (COD intent gated on payment_type)
    identity_ok = extracted.get("identity_verified") is True
    address_ok = extracted.get("address_confirmation") == "yes"
    avail_ok = extracted.get("availability") == "yes"
    cod_ok = (
        extracted.get("cod_intent") == "confirmed"
        if payment_type is PaymentType.COD
        else True
    )
    if identity_ok and address_ok and avail_ok and cod_ok:
        return Bucket.CONFIRMED

    # Fallback: anything not cleanly classified above goes to escalate
    return Bucket.ESCALATE

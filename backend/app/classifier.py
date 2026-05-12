from typing import Any

from .models import Bucket, PaymentType


def _truthy(value: Any) -> bool:
    """Return True for bool True, or strings 'true'/'yes'/'1' (any case)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def classify(extracted: dict[str, Any], payment_type: PaymentType) -> Bucket:
    """First-match-wins bucket assignment per new 8-field schema."""
    # Rule 1: escalate if escalate_to_human truthy OR delivery_confirmed == "no"
    if _truthy(extracted.get("escalate_to_human")) or extracted.get("delivery_confirmed") == "no":
        return Bucket.ESCALATE

    # Rule 2: cancel intent
    if extracted.get("intent") == "cancel":
        return Bucket.CANCEL_INTENT

    # Rule 3: address updated
    if extracted.get("address_correct") == "updated":
        return Bucket.ADDRESS_UPDATED

    # Rule 4: rescheduled
    if (
        extracted.get("delivery_confirmed") == "reschedule"
        or extracted.get("intent") == "reschedule"
    ):
        return Bucket.RESCHEDULED

    # Rule 5: confirmed — all positive signals present
    if (
        extracted.get("delivery_confirmed") == "yes"
        and extracted.get("address_correct") == "yes"
        and extracted.get("intent") == "keep"
    ):
        return Bucket.CONFIRMED

    # Fallback
    return Bucket.ESCALATE

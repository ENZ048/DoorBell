from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from .models import Order, PaymentType

REQUIRED_COLUMNS = {
    "order_id",
    "customer_name",
    "customer_phone",
    "product",
    "delivery_slot_label",
    "address",
    "pincode",
    "payment_type",
    "amount",
}


@dataclass
class RowError:
    row_number: int
    raw: dict
    reason: str


@dataclass
class ParseResult:
    inserted: list[Order] = field(default_factory=list)
    rejected: list[RowError] = field(default_factory=list)
    total_parsed: int = 0


def _normalize_phone(raw: str) -> str:
    """Normalize Indian mobile to E.164. Accepts +91xxxxxxxxxx, 91xxxxxxxxxx, or 10-digit."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        raise ValueError("phone is empty")
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    if (raw or "").startswith("+") and len(digits) >= 11:
        return "+" + digits
    raise ValueError("phone must be a valid Indian mobile (10 digits or E.164 +91...)")


def _placeholder_slot() -> str:
    """If CSV omits ISO interval, store a placeholder marking 'see label'."""
    return "label-only"


def _parse_row(row_number: int, raw: dict) -> Order:
    phone = _normalize_phone(raw.get("customer_phone", ""))
    try:
        amount = int(str(raw.get("amount", "")).strip())
    except (ValueError, TypeError) as e:
        raise ValueError(f"amount must be an integer: {e}") from e
    pt_raw = (raw.get("payment_type") or "").strip().upper()
    try:
        payment_type = PaymentType(pt_raw)
    except ValueError as e:
        raise ValueError(f"payment_type must be COD or PREPAID, got {pt_raw!r}") from e
    return Order(
        order_id=(raw.get("order_id") or "").strip(),
        customer_name=(raw.get("customer_name") or "").strip(),
        customer_phone=phone,
        product=(raw.get("product") or "").strip(),
        delivery_slot=(raw.get("delivery_slot") or "").strip() or _placeholder_slot(),
        delivery_slot_label=(raw.get("delivery_slot_label") or "").strip(),
        address=(raw.get("address") or "").strip(),
        pincode=(raw.get("pincode") or "").strip(),
        payment_type=payment_type,
        amount=amount,
    )


def parse_csv(body: bytes) -> ParseResult:
    text = body.decode("utf-8-sig")  # strips BOM if present
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("empty CSV")
    # Case-insensitive header normalization
    normalized = {f.lower().strip(): f for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - set(normalized.keys())
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    result = ParseResult()
    for idx, raw in enumerate(reader, start=2):  # row 1 is header
        result.total_parsed += 1
        canonical = {k: raw.get(normalized[k]) for k in REQUIRED_COLUMNS}
        try:
            order = _parse_row(idx, canonical)
        except (ValueError, ValidationError) as e:
            result.rejected.append(RowError(row_number=idx, raw=canonical, reason=str(e)))
            continue
        result.inserted.append(order)
    return result

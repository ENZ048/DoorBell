from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CallStatus(str, Enum):
    PENDING = "pending"
    DIALING = "dialing"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class PaymentType(str, Enum):
    COD = "COD"
    PREPAID = "PREPAID"


class Bucket(str, Enum):
    CONFIRMED = "confirmed"
    ADDRESS_UPDATED = "address_updated"
    RESCHEDULED = "rescheduled"
    CANCEL_INTENT = "cancel_intent"
    ESCALATE = "escalate"


class ActionState(str, Enum):
    DISPATCHED = "dispatched"
    CANCELLED = "cancelled"
    RESCHEDULED_CONFIRMED = "rescheduled_confirmed"
    ADDRESS_PUSHED = "address_pushed"
    HUMAN_ASSIGNED = "human_assigned"


class TranscriptTurn(BaseModel):
    role: str  # "agent" | "customer"
    speaker_label: str = ""
    text: str
    ts: datetime | None = None


class Action(BaseModel):
    action: str
    note: str | None = None
    by: str = "seller"
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Order(BaseModel):
    order_id: str
    customer_name: str
    customer_phone: str
    product: str
    delivery_slot: str
    delivery_slot_label: str
    address: str
    pincode: str
    payment_type: PaymentType
    amount: int

    call_status: CallStatus = CallStatus.PENDING
    bolna_call_id: str | None = None
    bucket: Bucket | None = None
    action_state: ActionState | None = None

    transcript: list[TranscriptTurn] = Field(default_factory=list)
    recording_url: str | None = None
    extracted_variables: dict[str, Any] = Field(default_factory=dict)
    updated_address: str | None = None
    reschedule_preference: str | None = None

    actions: list[Action] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("customer_phone")
    @classmethod
    def _phone_must_be_e164(cls, v: str) -> str:
        if not v.startswith("+") or not v[1:].isdigit() or len(v) < 11:
            raise ValueError("customer_phone must be E.164 (e.g., +919876543210)")
        return v


class CallEvent(BaseModel):
    order_id: str
    type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=_utcnow)

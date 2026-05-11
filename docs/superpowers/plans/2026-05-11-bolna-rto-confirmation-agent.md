# Riya Pre-Delivery Confirmation Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Riya Hinglish voice agent (configured on Bolna) plus a FastAPI + React seller ops console that ingests CSV orders, places live confirmation calls via Bolna, classifies outcomes into 5 buckets, surfaces them on a live-updating dashboard, and lets the seller act before dispatch.

**Architecture:** Single EC2 (ap-south-1) running Docker Compose with two services — Caddy (TLS + static + reverse-proxy with SSE-friendly flushing) and FastAPI (single Uvicorn worker for in-process SSE pubsub). MongoDB Atlas M0 (Mumbai) for persistence. Bolna external for voice. CSV upload simulates the OMS "Out for Delivery" trigger. Demo plays one real call + two pre-staged outcomes.

**Tech Stack:**
- Backend: Python 3.12, FastAPI 0.118+, Uvicorn, Motor 3.6+ (async Mongo), Pydantic v2, httpx, python-multipart, pytest, mongomock-motor, respx, ruff
- Frontend: Node 22 LTS, Vite 6, React 19, TypeScript 5.6, Tailwind 3.4, shadcn/ui primitives, Zustand 5
- Infra: Docker Compose, Caddy 2-alpine, MongoDB Atlas M0
- CI: GitHub Actions free tier

**Spec reference:** `docs/superpowers/specs/2026-05-11-bolna-rto-confirmation-agent-design.md`

---

## File structure (locked at planning time)

```
/
├── .gitignore                                  # Already exists from spec commit
├── README.md                                   # Task 34
├── .env.example                                # Task 1
├── docker-compose.yml                          # Task 32
├── Caddyfile                                   # Task 32
├── deploy.sh                                   # Task 33
├── .github/workflows/ci.yml                    # Task 35
├── docs/
│   ├── superpowers/{specs,plans}/              # Exists
│   ├── bolna-agent-prompt.md                   # Task 36 — Riya prompt + var schema
│   └── dry-run-checklist.md                    # Task 37
├── scripts/
│   └── demo_orders.csv                         # Task 37
├── backend/
│   ├── Dockerfile                              # Task 30
│   ├── pyproject.toml                          # Task 2
│   ├── pytest.ini                              # Task 2
│   ├── app/
│   │   ├── __init__.py                         # Task 2
│   │   ├── main.py                             # Task 2 (skeleton), grown across tasks
│   │   ├── config.py                           # Task 2 — env-var settings
│   │   ├── db.py                               # Task 3 — Mongo client + collection accessors
│   │   ├── models.py                           # Task 4 — Pydantic schemas
│   │   ├── csv_parser.py                       # Task 5
│   │   ├── classifier.py                       # Task 6
│   │   ├── auth.py                             # Task 7 — HMAC + admin token verify
│   │   ├── bolna.py                            # Task 8 — Bolna client
│   │   ├── pubsub.py                           # Task 12 — in-process asyncio pubsub
│   │   ├── sweeper.py                          # Task 18
│   │   └── routers/
│   │       ├── __init__.py                     # Task 9
│   │       ├── orders.py                       # Tasks 9, 10
│   │       ├── calls.py                        # Task 11
│   │       ├── webhook.py                      # Task 13
│   │       ├── actions.py                      # Task 14
│   │       ├── stats.py                        # Task 15
│   │       ├── demo.py                         # Task 16 — admin: simulate, reset
│   │       └── stream.py                       # Task 17
│   └── tests/
│       ├── __init__.py                         # Task 2
│       ├── conftest.py                         # Task 3 — app + mongo fixtures
│       ├── test_csv_parser.py                  # Task 5
│       ├── test_classifier.py                  # Task 6
│       ├── test_auth.py                        # Task 7
│       ├── test_bolna.py                       # Task 8
│       ├── test_orders.py                      # Tasks 9, 10
│       ├── test_calls.py                       # Task 11
│       ├── test_pubsub.py                      # Task 12
│       ├── test_webhook.py                     # Task 13
│       ├── test_actions.py                     # Task 14
│       ├── test_stats.py                       # Task 15
│       ├── test_demo.py                        # Task 16
│       └── test_stream.py                      # Task 17
└── frontend/
    ├── Dockerfile                              # Task 31
    ├── package.json                            # Task 19
    ├── tsconfig.json                           # Task 19
    ├── vite.config.ts                          # Task 19
    ├── tailwind.config.js                      # Task 19
    ├── postcss.config.js                       # Task 19
    ├── index.html                              # Task 19
    └── src/
        ├── main.tsx                            # Task 19
        ├── App.tsx                             # Task 19, grown across tasks
        ├── index.css                           # Task 19
        ├── types.ts                            # Task 20
        ├── api.ts                              # Task 20
        ├── store.ts                            # Task 21
        ├── sse.ts                              # Task 28
        ├── lib/
        │   └── format.ts                       # Task 20 — bucket colors, currency
        └── components/
            ├── TopBar.tsx                      # Task 22
            ├── UploadModal.tsx                 # Task 23
            ├── OrderTable.tsx                  # Task 24
            ├── OrderRow.tsx                    # Task 24
            ├── BucketTabs.tsx                  # Task 25
            ├── OrderDrawer.tsx                 # Task 26
            ├── ImpactStrip.tsx                 # Task 27
            ├── ConnectionDot.tsx               # Task 28
            └── DemoControlsMenu.tsx            # Task 29
```

---

## Phase A — Foundations (Tasks 1-4)

### Task 1: Repo bootstrap, .env.example, directory scaffold

**Files:**
- Create: `.env.example`
- Create: `backend/`, `frontend/`, `scripts/`, `.github/workflows/` directory placeholders

- [ ] **Step 1: Create directory placeholders**

```bash
mkdir -p backend/app/routers backend/tests frontend/src/components frontend/src/lib scripts .github/workflows docs/superpowers/plans
```

- [ ] **Step 2: Create `.env.example`**

```bash
cat > .env.example <<'EOF'
# Public domain that Caddy will obtain TLS for
DOMAIN=riya.example.com
PUBLIC_BASE_URL=https://riya.example.com

# MongoDB Atlas connection string (M0 free tier, ap-south-1)
MONGODB_URI=mongodb+srv://USER:PASS@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=riya

# Bolna credentials and agent
BOLNA_API_KEY=
BOLNA_AGENT_ID=
BOLNA_WEBHOOK_SECRET=

# Admin token (random 32+ chars) for demo helper endpoints
ADMIN_TOKEN=
EOF
```

- [ ] **Step 3: Commit**

```bash
git add .env.example backend frontend scripts .github
git commit -m "Bootstrap repo skeleton + env example"
```

---

### Task 2: Backend project skeleton + /health endpoint + pytest config

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "riya-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.118.0",
  "uvicorn[standard]==0.32.0",
  "motor==3.6.0",
  "pydantic==2.9.2",
  "pydantic-settings==2.6.0",
  "python-multipart==0.0.12",
  "httpx==0.27.2",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.3",
  "pytest-asyncio==0.24.0",
  "mongomock-motor==0.0.34",
  "respx==0.21.1",
  "ruff==0.7.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```

- [ ] **Step 2: Write `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = -ra -q
```

- [ ] **Step 3: Write `backend/app/__init__.py`** — empty file

```python
```

- [ ] **Step 4: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "riya"
    bolna_api_key: str = ""
    bolna_agent_id: str = ""
    bolna_webhook_secret: str = ""
    bolna_base_url: str = "https://api.bolna.dev"
    admin_token: str = "dev-admin-token"
    public_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
```

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Riya Backend", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "riya-backend"}

    @app.get("/api/version")
    async def version() -> dict:
        return {"version": app.version}

    return app


app = create_app()
```

- [ ] **Step 6: Write `backend/tests/__init__.py`** — empty file

```python
```

- [ ] **Step 7: Write the failing test `backend/tests/test_health.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "riya-backend"}


@pytest.mark.asyncio
async def test_version_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}
```

- [ ] **Step 8: Install deps and run tests**

Run:
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest -v
```

Expected: 2 PASSED.

- [ ] **Step 9: Commit**

```bash
cd ..
git add backend/pyproject.toml backend/pytest.ini backend/app backend/tests
git commit -m "Backend skeleton: FastAPI app + health/version endpoints + pytest"
```

---

### Task 3: MongoDB connection module + pytest fixtures

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/tests/conftest.py`
- Modify: `backend/app/main.py` — wire Mongo into app state on startup

- [ ] **Step 1: Write `backend/app/db.py`**

```python
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings


class Database:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


database = Database()


async def connect(client: AsyncIOMotorClient | None = None) -> None:
    """Connect to Mongo. Pass `client` to inject (e.g., mongomock) in tests."""
    database.client = client or AsyncIOMotorClient(settings.mongodb_uri)
    database.db = database.client[settings.mongodb_db]


async def disconnect() -> None:
    if database.client is not None:
        database.client.close()
        database.client = None
        database.db = None


def orders() -> Any:
    assert database.db is not None, "DB not initialized"
    return database.db["orders"]


def call_events() -> Any:
    assert database.db is not None, "DB not initialized"
    return database.db["call_events"]


async def ensure_indexes() -> None:
    await orders().create_index("bolna_call_id", unique=True, sparse=True)
    await orders().create_index([("created_at", -1)])
    await orders().create_index("bucket")
    await call_events().create_index([("order_id", 1), ("ts", 1)])
```

- [ ] **Step 2: Modify `backend/app/main.py` to attach startup/shutdown handlers**

Replace contents with:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.ensure_indexes()
    yield
    await db.disconnect()


def create_app(lifespan_fn=lifespan) -> FastAPI:
    app = FastAPI(title="Riya Backend", version="0.1.0", lifespan=lifespan_fn)

    @app.get("/health")
    async def health() -> dict:
        mongo_ok = db.database.db is not None
        return {"ok": True, "service": "riya-backend", "mongo": mongo_ok}

    @app.get("/api/version")
    async def version() -> dict:
        return {"version": app.version}

    return app


app = create_app()
```

- [ ] **Step 3: Write `backend/tests/conftest.py`**

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app import db
from app.main import create_app


@pytest_asyncio.fixture
async def mock_db():
    """Fresh in-memory Mongo for each test."""
    client = AsyncMongoMockClient()
    await db.connect(client=client)
    await db.ensure_indexes()
    yield db.database.db
    await db.disconnect()


@pytest_asyncio.fixture
async def client(mock_db):
    """HTTP client bound to the FastAPI app, with mock Mongo already wired."""

    # We bypass create_app's lifespan because mock_db already connected.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = create_app(lifespan_fn=noop_lifespan)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

- [ ] **Step 4: Update `backend/tests/test_health.py` to use the client fixture**

```python
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["service"] == "riya-backend"
    assert body["mongo"] is True


@pytest.mark.asyncio
async def test_version_endpoint(client):
    response = await client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}
```

- [ ] **Step 5: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/db.py backend/app/main.py backend/tests/conftest.py backend/tests/test_health.py
git commit -m "Mongo connection module + lifespan + test fixtures"
```

---

### Task 4: Pydantic models for Order and CallEvent

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_models.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Write `backend/app/models.py`**

```python
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
```

- [ ] **Step 4: Run test to verify pass**

```bash
pytest tests/test_models.py -v
```

Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/models.py backend/tests/test_models.py
git commit -m "Pydantic models for Order, Action, CallEvent + enums"
```

---

## Phase B — Core business logic (Tasks 5-8)

### Task 5: CSV parser with phone normalization

**Files:**
- Create: `backend/app/csv_parser.py`
- Create: `backend/tests/test_csv_parser.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_csv_parser.py`**

```python
from io import StringIO

import pytest

from app.csv_parser import ParseResult, parse_csv


def _csv(rows: list[str]) -> bytes:
    header = "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount"
    return ("\n".join([header, *rows])).encode("utf-8")


def test_happy_path_single_row():
    body = _csv([
        "SNT-1,Ananya Sharma,+919876543210,Snitch Tee,kal subah 10-1,B-204 BLR,560038,COD,1499"
    ])
    result: ParseResult = parse_csv(body)
    assert result.total_parsed == 1
    assert len(result.inserted) == 1
    assert result.rejected == []
    o = result.inserted[0]
    assert o.order_id == "SNT-1"
    assert o.customer_phone == "+919876543210"
    assert o.amount == 1499
    assert o.payment_type.value == "COD"


def test_normalizes_indian_phone_without_plus():
    body = _csv([
        "SNT-2,Rohit,9876543210,Tee,kal,addr,560001,PREPAID,999"
    ])
    result = parse_csv(body)
    assert len(result.inserted) == 1
    assert result.inserted[0].customer_phone == "+919876543210"


def test_normalizes_10_digit_with_91_prefix():
    body = _csv([
        "SNT-3,Priya,91 9876543210,Tee,kal,addr,560001,PREPAID,999"
    ])
    result = parse_csv(body)
    assert result.inserted[0].customer_phone == "+919876543210"


def test_rejects_invalid_phone():
    body = _csv([
        "SNT-4,X,12345,Tee,kal,addr,560001,COD,100"
    ])
    result = parse_csv(body)
    assert result.inserted == []
    assert len(result.rejected) == 1
    assert "phone" in result.rejected[0].reason.lower()
    assert result.rejected[0].row_number == 2  # header is row 1


def test_rejects_invalid_amount():
    body = _csv([
        "SNT-5,X,+919876543210,Tee,kal,addr,560001,COD,not_a_number"
    ])
    result = parse_csv(body)
    assert result.inserted == []
    assert len(result.rejected) == 1
    assert "amount" in result.rejected[0].reason.lower()


def test_rejects_unknown_payment_type():
    body = _csv([
        "SNT-6,X,+919876543210,Tee,kal,addr,560001,UPI,100"
    ])
    result = parse_csv(body)
    assert result.inserted == []
    assert "payment_type" in result.rejected[0].reason.lower()


def test_case_insensitive_headers():
    header = "Order_ID,Customer_Name,Customer_Phone,Product,Delivery_Slot_Label,Address,Pincode,Payment_Type,Amount"
    body = (header + "\nSNT-7,A,+919876543210,P,kal,addr,560001,COD,500").encode("utf-8")
    result = parse_csv(body)
    assert len(result.inserted) == 1


def test_missing_required_column():
    body = b"order_id,customer_name\nSNT-8,X"
    with pytest.raises(ValueError, match="missing columns"):
        parse_csv(body)


def test_handles_bom():
    csv_text = "﻿order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\nSNT-9,A,+919876543210,P,kal,addr,560001,COD,500"
    result = parse_csv(csv_text.encode("utf-8"))
    assert len(result.inserted) == 1


def test_partial_success_mixed_rows():
    body = _csv([
        "SNT-10,A,+919876543210,P,kal,addr,560001,COD,500",
        "SNT-11,B,bad,P,kal,addr,560001,COD,500",
        "SNT-12,C,+919876543211,P,kal,addr,560001,PREPAID,800",
    ])
    result = parse_csv(body)
    assert result.total_parsed == 3
    assert len(result.inserted) == 2
    assert len(result.rejected) == 1
    assert result.rejected[0].row_number == 3
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && pytest tests/test_csv_parser.py -v
```

Expected: collection error / module not found.

- [ ] **Step 3: Write `backend/app/csv_parser.py`**

```python
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


def _placeholder_slot() -> str:
    """If CSV omits ISO interval, store a placeholder marking 'see label'."""
    return "label-only"


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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_csv_parser.py -v
```

Expected: 10 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/csv_parser.py backend/tests/test_csv_parser.py
git commit -m "CSV parser with phone normalization and per-row error reporting"
```

---

### Task 6: Bucket classifier (deterministic, table-driven test)

**Files:**
- Create: `backend/app/classifier.py`
- Create: `backend/tests/test_classifier.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_classifier.py`**

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_classifier.py -v
```

- [ ] **Step 3: Write `backend/app/classifier.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_classifier.py -v
```

Expected: 13 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/classifier.py backend/tests/test_classifier.py
git commit -m "Bucket classifier with deterministic priority order"
```

---

### Task 7: HMAC signature verifier + admin token guard

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_auth.py`**

```python
import hashlib
import hmac

import pytest
from fastapi import HTTPException

from app.auth import require_admin_token, verify_bolna_signature


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_bolna_signature_accepts_valid():
    body = b'{"x":1}'
    sig = sign("topsecret", body)
    assert verify_bolna_signature(body, sig, "topsecret") is True


def test_verify_bolna_signature_rejects_tampered_body():
    body = b'{"x":1}'
    sig = sign("topsecret", body)
    assert verify_bolna_signature(b'{"x":2}', sig, "topsecret") is False


def test_verify_bolna_signature_rejects_wrong_secret():
    body = b'{"x":1}'
    sig = sign("topsecret", body)
    assert verify_bolna_signature(body, sig, "different") is False


def test_verify_bolna_signature_rejects_malformed_header():
    body = b'{"x":1}'
    assert verify_bolna_signature(body, "not-hex", "topsecret") is False


def test_verify_bolna_signature_empty_secret_skips_verification():
    """If we don't have a secret configured, treat as unverified (caller decides)."""
    assert verify_bolna_signature(b"anything", "any", "") is False


def test_require_admin_token_accepts():
    require_admin_token("expected", "expected")  # should not raise


def test_require_admin_token_rejects_wrong():
    with pytest.raises(HTTPException) as exc:
        require_admin_token("wrong", "expected")
    assert exc.value.status_code == 401


def test_require_admin_token_rejects_empty():
    with pytest.raises(HTTPException):
        require_admin_token(None, "expected")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_auth.py -v
```

- [ ] **Step 3: Write `backend/app/auth.py`**

```python
import hashlib
import hmac

from fastapi import HTTPException


def verify_bolna_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """Constant-time HMAC-SHA256 verification of Bolna webhook signature."""
    if not secret or not signature_header:
        return False
    try:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    except Exception:
        return False
    return hmac.compare_digest(expected, signature_header.strip())


def require_admin_token(provided: str | None, expected: str) -> None:
    """Raises 401 if the X-Admin-Token header doesn't match."""
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid admin token")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_auth.py -v
```

Expected: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/auth.py backend/tests/test_auth.py
git commit -m "HMAC signature verification + admin token guard"
```

---

### Task 8: Bolna API client (create call) with respx mocking

**Files:**
- Create: `backend/app/bolna.py`
- Create: `backend/tests/test_bolna.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_bolna.py`**

```python
import httpx
import pytest
import respx

from app.bolna import BolnaClient, BolnaError


@pytest.mark.asyncio
async def test_create_call_posts_with_correct_payload(respx_mock):
    route = respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(200, json={"call_id": "bolna_abc123"})
    )
    client = BolnaClient(api_key="key123", base_url="https://api.bolna.dev")
    call_id = await client.create_call(
        agent_id="agent_riya",
        recipient_phone="+919876543210",
        variables={"customer_name": "Ananya", "order_id": "SNT-1"},
        webhook_url="https://riya.example.com/webhook/bolna",
    )
    assert call_id == "bolna_abc123"
    assert route.called
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer key123"
    body = req.read()
    assert b'"agent_id":"agent_riya"' in body or b'"agent_id": "agent_riya"' in body
    assert b"+919876543210" in body
    assert b"Ananya" in body


@pytest.mark.asyncio
async def test_create_call_raises_on_4xx(respx_mock):
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(400, json={"error": "bad agent"})
    )
    client = BolnaClient(api_key="k", base_url="https://api.bolna.dev")
    with pytest.raises(BolnaError):
        await client.create_call(
            agent_id="x", recipient_phone="+919999999999", variables={}, webhook_url="https://x"
        )


@pytest.mark.asyncio
async def test_create_call_raises_on_network_error(respx_mock):
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(side_effect=httpx.ConnectError("nope"))
    client = BolnaClient(api_key="k", base_url="https://api.bolna.dev")
    with pytest.raises(BolnaError):
        await client.create_call(
            agent_id="x", recipient_phone="+919999999999", variables={}, webhook_url="https://x"
        )
```

Add to `pyproject.toml` dev deps if not present: `respx==0.21.1` is already listed.

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_bolna.py -v
```

- [ ] **Step 3: Write `backend/app/bolna.py`**

```python
from __future__ import annotations

import httpx


class BolnaError(Exception):
    """Raised when Bolna API call fails."""


class BolnaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.bolna.dev", timeout: float = 10.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_call(
        self,
        agent_id: str,
        recipient_phone: str,
        variables: dict,
        webhook_url: str,
    ) -> str:
        """POST /v2/calls — returns Bolna call_id on success."""
        payload = {
            "agent_id": agent_id,
            "recipient_phone": recipient_phone,
            "variables": variables,
            "webhook_url": webhook_url,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/v2/calls", json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise BolnaError(f"network error calling Bolna: {e}") from e
        if resp.status_code >= 400:
            raise BolnaError(f"Bolna returned {resp.status_code}: {resp.text}")
        data = resp.json()
        # Defensive: Bolna may return id under various keys; check a few.
        for key in ("call_id", "id", "callId"):
            if key in data:
                return str(data[key])
        raise BolnaError(f"unexpected Bolna response shape: {data}")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_bolna.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/bolna.py backend/tests/test_bolna.py
git commit -m "Bolna API client with create_call + respx-mocked tests"
```

---

## Phase C — API endpoints (Tasks 9-11)

### Task 9: POST /api/orders/upload + router scaffolding

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/orders.py`
- Modify: `backend/app/main.py` — register orders router
- Create: `backend/tests/test_orders.py`

- [ ] **Step 1: Write `backend/app/routers/__init__.py`** — empty file

```python
```

- [ ] **Step 2: Write the failing test `backend/tests/test_orders.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_upload_inserts_valid_rows(client):
    csv_body = (
        "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\n"
        "SNT-1,Ananya,+919876543210,Tee,kal subah,addr,560038,COD,1499\n"
        "SNT-2,Rohit,9876543211,Tee,kal,addr,560001,PREPAID,999\n"
    ).encode("utf-8")
    response = await client.post(
        "/api/orders/upload",
        files={"file": ("orders.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_parsed"] == 2
    assert len(data["inserted"]) == 2
    assert data["rejected"] == []
    assert data["inserted"][0]["order_id"] == "SNT-1"


@pytest.mark.asyncio
async def test_upload_reports_rejected_rows(client):
    csv_body = (
        "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\n"
        "SNT-3,X,bad,P,kal,addr,560001,COD,100\n"
        "SNT-4,Y,+919876543212,P,kal,addr,560001,PREPAID,500\n"
    ).encode("utf-8")
    response = await client.post(
        "/api/orders/upload",
        files={"file": ("orders.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_parsed"] == 2
    assert len(data["inserted"]) == 1
    assert len(data["rejected"]) == 1
    assert data["rejected"][0]["row_number"] == 2


@pytest.mark.asyncio
async def test_upload_missing_required_column_returns_422(client):
    csv_body = b"order_id,customer_name\nSNT-5,A"
    response = await client.post(
        "/api/orders/upload",
        files={"file": ("bad.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_CSV"


@pytest.mark.asyncio
async def test_upload_persists_to_mongo(client, mock_db):
    csv_body = (
        "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\n"
        "SNT-6,Z,+919876543213,P,kal,addr,560001,COD,777\n"
    ).encode("utf-8")
    await client.post("/api/orders/upload", files={"file": ("o.csv", csv_body, "text/csv")})
    docs = await mock_db["orders"].find().to_list(length=10)
    assert len(docs) == 1
    assert docs[0]["order_id"] == "SNT-6"
    assert docs[0]["call_status"] == "pending"
```

- [ ] **Step 3: Run to verify failure**

```bash
cd backend && pytest tests/test_orders.py -v
```

Expected: 404 or import errors.

- [ ] **Step 4: Write `backend/app/routers/orders.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, UploadFile

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
        )
    inserted_serialized: list[dict] = []
    now = datetime.now(timezone.utc)
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
```

Override FastAPI's default detail wrapping so that 422 returns `{"error": ...}` cleanly. Add at top of file in main app:

- [ ] **Step 5: Modify `backend/app/main.py` to register router + custom HTTPException handler**

Replace contents:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from . import db
from .routers import orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.ensure_indexes()
    yield
    await db.disconnect()


def create_app(lifespan_fn=lifespan) -> FastAPI:
    app = FastAPI(title="Riya Backend", version="0.1.0", lifespan=lifespan_fn)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # If detail is already shaped as {"error": {...}}, pass through. Otherwise wrap.
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
        )

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "riya-backend", "mongo": db.database.db is not None}

    @app.get("/api/version")
    async def version() -> dict:
        return {"version": app.version}

    app.include_router(orders.router)
    return app


app = create_app()
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_orders.py tests/test_health.py -v
```

Expected: 4 PASSED for test_orders + 2 for test_health.

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/app/main.py backend/app/routers backend/tests/test_orders.py
git commit -m "POST /api/orders/upload with per-row validation + Mongo persistence"
```

---

### Task 10: GET /api/orders + GET /api/orders/{id}

**Files:**
- Modify: `backend/app/routers/orders.py`
- Modify: `backend/tests/test_orders.py`

- [ ] **Step 1: Append failing tests to `backend/tests/test_orders.py`**

```python
@pytest.mark.asyncio
async def test_list_orders_returns_all(client, mock_db):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    await mock_db["orders"].insert_many([
        {"order_id": "A", "call_status": "pending", "created_at": now,
         "customer_name": "x", "customer_phone": "+919999999999",
         "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
         "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
         "transcript": [], "extracted_variables": {}, "actions": [],
         "updated_at": now, "bucket": None, "action_state": None,
         "bolna_call_id": None, "recording_url": None, "updated_address": None,
         "reschedule_preference": None},
        {"order_id": "B", "call_status": "completed", "bucket": "confirmed",
         "created_at": now, "customer_name": "x", "customer_phone": "+919999999998",
         "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
         "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
         "transcript": [], "extracted_variables": {}, "actions": [],
         "updated_at": now, "action_state": None,
         "bolna_call_id": None, "recording_url": None, "updated_address": None,
         "reschedule_preference": None},
    ])
    resp = await client.get("/api/orders")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["orders"]) == 2


@pytest.mark.asyncio
async def test_list_orders_filters_by_bucket(client, mock_db):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    base = {"customer_name": "x", "customer_phone": "+919999999999",
            "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
            "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
            "transcript": [], "extracted_variables": {}, "actions": [],
            "updated_at": now, "action_state": None,
            "bolna_call_id": None, "recording_url": None, "updated_address": None,
            "reschedule_preference": None, "created_at": now}
    await mock_db["orders"].insert_many([
        {**base, "order_id": "A", "call_status": "completed", "bucket": "confirmed"},
        {**base, "order_id": "B", "call_status": "completed", "bucket": "escalate"},
    ])
    resp = await client.get("/api/orders?bucket=confirmed")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["orders"]) == 1
    assert body["orders"][0]["order_id"] == "A"


@pytest.mark.asyncio
async def test_get_order_by_id_includes_events(client, mock_db):
    from datetime import datetime, timezone
    from bson import ObjectId
    now = datetime.now(timezone.utc)
    oid = ObjectId()
    await mock_db["orders"].insert_one({
        "_id": oid, "order_id": "X", "call_status": "pending",
        "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "transcript": [], "extracted_variables": {}, "actions": [],
        "created_at": now, "updated_at": now, "bucket": None, "action_state": None,
        "bolna_call_id": None, "recording_url": None, "updated_address": None,
        "reschedule_preference": None,
    })
    await mock_db["call_events"].insert_one({
        "order_id": oid, "type": "created", "source": "csv", "payload": {}, "ts": now,
    })
    resp = await client.get(f"/api/orders/{oid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == "X"
    assert len(body["events"]) == 1


@pytest.mark.asyncio
async def test_get_unknown_order_returns_404(client):
    from bson import ObjectId
    resp = await client.get(f"/api/orders/{ObjectId()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ORDER_NOT_FOUND"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && pytest tests/test_orders.py -v
```

- [ ] **Step 3: Append to `backend/app/routers/orders.py`**

Add these endpoints after the `upload_orders` route:

```python
from typing import Optional


@router.get("")
async def list_orders(
    call_status: Optional[str] = None,
    bucket: Optional[str] = None,
    action_state: Optional[str] = None,
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
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": f"invalid id {order_id}"}},
        )
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_orders.py -v
```

Expected: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/routers/orders.py backend/tests/test_orders.py
git commit -m "GET /api/orders + GET /api/orders/{id} with filters and events"
```

---

### Task 11: POST /api/orders/{id}/call + /call-batch

**Files:**
- Create: `backend/app/routers/calls.py`
- Modify: `backend/app/main.py` — register calls router
- Create: `backend/tests/test_calls.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_calls.py`**

```python
from datetime import datetime, timezone

import httpx
import pytest
import respx
from bson import ObjectId


def _base_order(order_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "order_id": order_id,
        "customer_name": "Ananya",
        "customer_phone": "+919876543210",
        "product": "Tee",
        "delivery_slot": "x",
        "delivery_slot_label": "kal subah",
        "address": "addr",
        "pincode": "560001",
        "payment_type": "COD",
        "amount": 1499,
        "call_status": "pending",
        "bolna_call_id": None,
        "bucket": None,
        "action_state": None,
        "transcript": [],
        "extracted_variables": {},
        "actions": [],
        "recording_url": None,
        "updated_address": None,
        "reschedule_preference": None,
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_trigger_call_marks_dialing(client, mock_db, respx_mock):
    oid = (await mock_db["orders"].insert_one(_base_order("SNT-1"))).inserted_id
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(200, json={"call_id": "bolna_xyz"})
    )
    resp = await client.post(f"/api/orders/{oid}/call")
    assert resp.status_code == 202
    body = resp.json()
    assert body["call_status"] == "dialing"
    assert body["bolna_call_id"] == "bolna_xyz"
    doc = await mock_db["orders"].find_one({"_id": oid})
    assert doc["call_status"] == "dialing"
    assert doc["bolna_call_id"] == "bolna_xyz"


@pytest.mark.asyncio
async def test_trigger_call_handles_bolna_failure(client, mock_db, respx_mock):
    oid = (await mock_db["orders"].insert_one(_base_order("SNT-2"))).inserted_id
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(500, text="boom")
    )
    resp = await client.post(f"/api/orders/{oid}/call")
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "BOLNA_API_FAILED"
    doc = await mock_db["orders"].find_one({"_id": oid})
    assert doc["call_status"] == "failed"


@pytest.mark.asyncio
async def test_call_batch_triggers_multiple(client, mock_db, respx_mock):
    ids = []
    for n in range(3):
        r = await mock_db["orders"].insert_one(_base_order(f"SNT-{n}"))
        ids.append(str(r.inserted_id))
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(200, json={"call_id": "bolna_id"})
    )
    resp = await client.post("/api/orders/call-batch", json={"order_ids": ids})
    assert resp.status_code == 202
    body = resp.json()
    assert len(body["triggered"]) == 3
    assert body["failed"] == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_calls.py -v
```

- [ ] **Step 3: Write `backend/app/routers/calls.py`**

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..bolna import BolnaClient, BolnaError
from ..config import settings

router = APIRouter(prefix="/api/orders", tags=["calls"])


def _bolna_client() -> BolnaClient:
    return BolnaClient(api_key=settings.bolna_api_key, base_url=settings.bolna_base_url)


def _webhook_url() -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/webhook/bolna"


def _variables(doc: dict, brand_name: str = "Snitch") -> dict:
    addr = doc.get("address", "")
    address_short = addr.split(",")[0] if "," in addr else addr
    return {
        "customer_name": doc.get("customer_name", ""),
        "brand_name": brand_name,
        "order_id": doc.get("order_id", ""),
        "product": doc.get("product", ""),
        "delivery_slot_label": doc.get("delivery_slot_label", ""),
        "address_short": address_short,
        "payment_type": doc.get("payment_type", ""),
        "amount": doc.get("amount", 0),
    }


async def _dispatch_one(order_id: ObjectId, doc: dict) -> dict:
    now = datetime.now(timezone.utc)
    client = _bolna_client()
    try:
        call_id = await client.create_call(
            agent_id=settings.bolna_agent_id,
            recipient_phone=doc["customer_phone"],
            variables=_variables(doc),
            webhook_url=_webhook_url(),
        )
    except BolnaError as e:
        await db.orders().update_one(
            {"_id": order_id},
            {"$set": {"call_status": "failed", "updated_at": now}},
        )
        await db.call_events().insert_one(
            {"order_id": order_id, "type": "error", "source": "bolna",
             "payload": {"message": str(e)}, "ts": now},
        )
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "BOLNA_API_FAILED", "message": str(e)}},
        )
    await db.orders().update_one(
        {"_id": order_id},
        {"$set": {"call_status": "dialing", "bolna_call_id": call_id, "updated_at": now}},
    )
    await db.call_events().insert_one(
        {"order_id": order_id, "type": "call_initiated", "source": "api",
         "payload": {"bolna_call_id": call_id}, "ts": now},
    )
    return {"call_status": "dialing", "bolna_call_id": call_id}


@router.post("/{order_id}/call")
async def trigger_call(order_id: str):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "invalid id"}},
        )
    doc = await db.orders().find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "order not found"}},
        )
    result = await _dispatch_one(oid, doc)
    return result


class BatchRequest(BaseModel):
    order_ids: list[str] | None = None
    all_pending: bool = False


@router.post("/call-batch")
async def trigger_batch(req: BatchRequest):
    if req.all_pending:
        cursor = db.orders().find({"call_status": "pending"}).limit(100)
        docs = await cursor.to_list(length=100)
    else:
        if not req.order_ids:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "INVALID_REQUEST",
                                  "message": "order_ids required when all_pending=false"}},
            )
        oids = [ObjectId(x) for x in req.order_ids]
        cursor = db.orders().find({"_id": {"$in": oids}})
        docs = await cursor.to_list(length=len(oids))

    sem = asyncio.Semaphore(3)
    triggered: list[dict] = []
    failed: list[dict] = []

    async def _safe(doc):
        async with sem:
            try:
                res = await _dispatch_one(doc["_id"], doc)
                triggered.append({"order_id": str(doc["_id"]), **res})
            except HTTPException as e:
                failed.append({"order_id": str(doc["_id"]), "error": e.detail})

    await asyncio.gather(*[_safe(d) for d in docs])
    return {"triggered": triggered, "failed": failed}
```

- [ ] **Step 4: Register router in `backend/app/main.py`**

Update the imports and `include_router` calls:

```python
from .routers import calls, orders
# ...
app.include_router(orders.router)
app.include_router(calls.router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_calls.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/routers/calls.py backend/app/main.py backend/tests/test_calls.py
git commit -m "POST /api/orders/{id}/call + /call-batch with Bolna dispatch"
```

---

## Phase D — Pubsub, webhook, actions, stats (Tasks 12-16)

### Task 12: In-process asyncio pubsub module

**Files:**
- Create: `backend/app/pubsub.py`
- Create: `backend/tests/test_pubsub.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_pubsub.py`**

```python
import asyncio

import pytest

from app.pubsub import PubSub


@pytest.mark.asyncio
async def test_subscriber_receives_published_event():
    bus = PubSub()
    async with bus.subscribe() as queue:
        await bus.publish({"event": "order.updated", "id": "x"})
        msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert msg == {"event": "order.updated", "id": "x"}


@pytest.mark.asyncio
async def test_multiple_subscribers_receive_same_event():
    bus = PubSub()
    async with bus.subscribe() as q1, bus.subscribe() as q2:
        await bus.publish({"event": "a"})
        m1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        m2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert m1 == {"event": "a"}
    assert m2 == {"event": "a"}


@pytest.mark.asyncio
async def test_unsubscribe_on_exit():
    bus = PubSub()
    async with bus.subscribe():
        assert len(bus._subscribers) == 1
    assert len(bus._subscribers) == 0


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_is_noop():
    bus = PubSub()
    await bus.publish({"event": "lonely"})  # must not raise
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_pubsub.py -v
```

- [ ] **Step 3: Write `backend/app/pubsub.py`**

```python
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class PubSub:
    def __init__(self, queue_maxsize: int = 100) -> None:
        self._subscribers: set[asyncio.Queue[Any]] = set()
        self._queue_maxsize = queue_maxsize

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[Any]]:
        q: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_maxsize)
        self._subscribers.add(q)
        try:
            yield q
        finally:
            self._subscribers.discard(q)

    async def publish(self, event: dict) -> None:
        # Best-effort fan-out. If a queue is full, drop the event for that subscriber
        # (preserves liveness for other subscribers).
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                continue


# Module-level singleton — single-worker assumption means one bus per process.
bus = PubSub()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_pubsub.py -v
```

Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/pubsub.py backend/tests/test_pubsub.py
git commit -m "In-process asyncio pubsub for SSE fan-out"
```

---

### Task 13: POST /webhook/bolna — the heart of the system

**Files:**
- Create: `backend/app/routers/webhook.py`
- Modify: `backend/app/main.py` — register webhook router
- Modify: `backend/app/routers/calls.py` — publish "order.updated" on dispatch
- Create: `backend/tests/test_webhook.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_webhook.py`**

```python
import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.config import settings
from app.pubsub import bus


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _base_doc(call_id: str, payment_type: str = "COD") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "order_id": "SNT-1", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": payment_type, "amount": 1499,
        "call_status": "dialing", "bolna_call_id": call_id, "bucket": None,
        "action_state": None, "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


@pytest.mark.asyncio
async def test_webhook_classifies_confirmed(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")  # disable HMAC for this test
    await mock_db["orders"].insert_one(_base_doc("bolna_a"))
    payload = {
        "call_id": "bolna_a",
        "transcript": [{"role": "agent", "text": "Namaste..."}],
        "recording_url": "https://example.com/rec.mp3",
        "extracted_variables": {
            "identity_verified": True, "wrong_number": False,
            "address_confirmation": "yes", "availability": "yes",
            "cod_intent": "confirmed", "needs_human": False,
        },
    }
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_a"})
    assert doc["call_status"] == "completed"
    assert doc["bucket"] == "confirmed"
    assert doc["recording_url"] == "https://example.com/rec.mp3"


@pytest.mark.asyncio
async def test_webhook_classifies_cancel_intent(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_b", payment_type="COD"))
    payload = {
        "call_id": "bolna_b",
        "extracted_variables": {
            "identity_verified": True, "wrong_number": False,
            "address_confirmation": "yes", "availability": "yes",
            "cod_intent": "cancel", "needs_human": False,
        },
    }
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"bolna_call_id": "bolna_b"})
    assert doc["bucket"] == "cancel_intent"


@pytest.mark.asyncio
async def test_webhook_idempotent_when_already_bucketed(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    doc = _base_doc("bolna_c")
    doc["bucket"] = "confirmed"
    doc["call_status"] = "completed"
    await mock_db["orders"].insert_one(doc)
    payload = {"call_id": "bolna_c", "extracted_variables": {"cod_intent": "cancel"}}
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    after = await mock_db["orders"].find_one({"bolna_call_id": "bolna_c"})
    assert after["bucket"] == "confirmed"  # unchanged


@pytest.mark.asyncio
async def test_webhook_unknown_call_id_returns_200_but_logs(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    payload = {"call_id": "unknown", "extracted_variables": {}}
    resp = await client.post("/webhook/bolna", json=payload)
    assert resp.status_code == 200
    # an error event should be logged
    evs = await mock_db["call_events"].find({"type": "error"}).to_list(length=10)
    assert any("unknown" in str(e.get("payload", {})) for e in evs)


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "topsecret")
    await mock_db["orders"].insert_one(_base_doc("bolna_d"))
    resp = await client.post(
        "/webhook/bolna",
        json={"call_id": "bolna_d", "extracted_variables": {}},
        headers={"X-Bolna-Signature": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_publishes_to_pubsub(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "bolna_webhook_secret", "")
    await mock_db["orders"].insert_one(_base_doc("bolna_e"))
    async with bus.subscribe() as q:
        payload = {
            "call_id": "bolna_e",
            "extracted_variables": {
                "identity_verified": True, "address_confirmation": "yes",
                "availability": "yes", "cod_intent": "confirmed",
            },
        }
        await client.post("/webhook/bolna", json=payload)
        msg = await asyncio.wait_for(q.get(), timeout=1.0)
    assert msg["event"] == "order.updated"
    assert "snapshot" in msg
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_webhook.py -v
```

- [ ] **Step 3: Write `backend/app/routers/webhook.py`**

```python
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request

from .. import db
from ..auth import verify_bolna_signature
from ..classifier import classify
from ..config import settings
from ..models import Bucket, CallStatus, PaymentType
from ..pubsub import bus

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _projection(doc: dict) -> dict:
    """Minimal projection sent over SSE."""
    return {
        "_id": str(doc.get("_id")),
        "order_id": doc.get("order_id"),
        "call_status": doc.get("call_status"),
        "bucket": doc.get("bucket"),
        "action_state": doc.get("action_state"),
        "customer_name": doc.get("customer_name"),
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


@router.post("/bolna")
async def bolna_webhook(request: Request, x_bolna_signature: str | None = Header(default=None)):
    raw = await request.body()
    secret = settings.bolna_webhook_secret
    if secret:
        if not verify_bolna_signature(raw, x_bolna_signature, secret):
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "BAD_SIGNATURE", "message": "HMAC verification failed"}},
            )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_JSON", "message": "invalid JSON"}},
        )

    call_id = payload.get("call_id") or payload.get("callId") or payload.get("id")
    if not call_id:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "MISSING_CALL_ID", "message": "call_id required"}},
        )

    now = datetime.now(timezone.utc)
    doc = await db.orders().find_one({"bolna_call_id": call_id})
    if not doc:
        await db.call_events().insert_one(
            {"order_id": None, "type": "error", "source": "bolna",
             "payload": {"reason": "unknown call_id", "call_id": call_id}, "ts": now},
        )
        return {"ok": True}

    # Idempotency: don't re-bucket if already classified
    if doc.get("bucket"):
        await db.call_events().insert_one(
            {"order_id": doc["_id"], "type": "webhook_received", "source": "bolna",
             "payload": {"duplicate": True, "raw": payload}, "ts": now},
        )
        return {"ok": True}

    extracted = payload.get("extracted_variables", {}) or {}
    transcript = payload.get("transcript", []) or []
    recording_url = payload.get("recording_url")
    payment_type = PaymentType(doc.get("payment_type", "PREPAID"))
    bucket = classify(extracted, payment_type)

    update_fields = {
        "call_status": CallStatus.COMPLETED.value,
        "bucket": bucket.value,
        "transcript": transcript,
        "recording_url": recording_url,
        "extracted_variables": extracted,
        "updated_address": extracted.get("updated_address"),
        "reschedule_preference": extracted.get("reschedule_preference"),
        "updated_at": now,
    }

    await db.orders().update_one({"_id": doc["_id"]}, {"$set": update_fields})

    await db.call_events().insert_one(
        {"order_id": doc["_id"], "type": "webhook_received", "source": "bolna",
         "payload": payload, "ts": now},
    )
    await db.call_events().insert_one(
        {"order_id": doc["_id"], "type": "bucketed", "source": "bolna",
         "payload": {"bucket": bucket.value}, "ts": now},
    )

    fresh = await db.orders().find_one({"_id": doc["_id"]})
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})

    return {"ok": True}
```

- [ ] **Step 4: Add pubsub publish to `backend/app/routers/calls.py`**

Inside `_dispatch_one` after the successful `update_one` (and before the return), add:

```python
    fresh = await db.orders().find_one({"_id": order_id})
    from ..pubsub import bus
    from ..routers.webhook import _projection
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})
```

- [ ] **Step 5: Register webhook router in `backend/app/main.py`**

```python
from .routers import calls, orders, webhook
# ...
app.include_router(webhook.router)
```

- [ ] **Step 6: Run all tests**

```bash
pytest -v
```

Expected: all previous tests + 6 new ones pass.

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/app/routers/webhook.py backend/app/main.py backend/app/routers/calls.py backend/tests/test_webhook.py
git commit -m "POST /webhook/bolna with HMAC verify, classifier, idempotency, pubsub fan-out"
```

---

### Task 14: POST /api/orders/{id}/action — seller actions

**Files:**
- Create: `backend/app/routers/actions.py`
- Modify: `backend/app/main.py` — register actions router
- Create: `backend/tests/test_actions.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_actions.py`**

```python
from datetime import datetime, timezone

import pytest


def _doc(bucket: str | None = None, action_state: str | None = None):
    now = datetime.now(timezone.utc)
    return {
        "order_id": "SNT-1", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "call_status": "completed", "bucket": bucket, "action_state": action_state,
        "bolna_call_id": "x", "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


@pytest.mark.asyncio
async def test_approve_dispatch_on_confirmed(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="confirmed"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "approve_dispatch", "note": "go"},
    )
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"_id": res.inserted_id})
    assert doc["action_state"] == "dispatched"
    assert len(doc["actions"]) == 1
    assert doc["actions"][0]["action"] == "approve_dispatch"


@pytest.mark.asyncio
async def test_push_new_address_requires_address_updated_bucket(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="confirmed"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "push_new_address"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_ACTION_FOR_BUCKET"


@pytest.mark.asyncio
async def test_push_new_address_on_address_updated(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="address_updated"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "push_new_address"},
    )
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"_id": res.inserted_id})
    assert doc["action_state"] == "address_pushed"


@pytest.mark.asyncio
async def test_unknown_action_rejected(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc(bucket="confirmed"))
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/action",
        json={"action": "made_up"},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_actions.py -v
```

- [ ] **Step 3: Write `backend/app/routers/actions.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..pubsub import bus
from ..routers.webhook import _projection

router = APIRouter(prefix="/api/orders", tags=["actions"])

# Map action → derived action_state, and which buckets each action is valid for
ACTION_MAP: dict[str, tuple[str, set[str]]] = {
    "approve_dispatch": (
        "dispatched",
        {"confirmed", "address_updated", "rescheduled", "escalate"},
    ),
    "cancel_dispatch": (
        "cancelled",
        {"confirmed", "address_updated", "rescheduled", "cancel_intent", "escalate",
         "no_answer", "failed"},
    ),
    "push_new_address": ("address_pushed", {"address_updated"}),
    "confirm_reschedule": ("rescheduled_confirmed", {"rescheduled"}),
    "assign_human": (
        "human_assigned",
        {"escalate", "cancel_intent", "confirmed", "address_updated", "rescheduled",
         "no_answer", "failed"},
    ),
}


class ActionRequest(BaseModel):
    action: str
    note: str | None = None


@router.post("/{order_id}/action")
async def record_action(order_id: str, req: ActionRequest):
    if req.action not in ACTION_MAP:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNKNOWN_ACTION", "message": f"unknown action {req.action}"}},
        )
    action_state, valid_buckets = ACTION_MAP[req.action]
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "invalid id"}},
        )
    doc = await db.orders().find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "order not found"}},
        )

    current_bucket = doc.get("bucket") or doc.get("call_status")  # allow no_answer/failed
    if current_bucket not in valid_buckets:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_ACTION_FOR_BUCKET",
                              "message": f"action {req.action} not valid for {current_bucket}"}},
        )

    now = datetime.now(timezone.utc)
    action_entry = {"action": req.action, "note": req.note, "by": "seller", "ts": now}
    await db.orders().update_one(
        {"_id": oid},
        {
            "$push": {"actions": action_entry},
            "$set": {"action_state": action_state, "updated_at": now},
        },
    )
    await db.call_events().insert_one(
        {"order_id": oid, "type": "action_taken", "source": "seller",
         "payload": action_entry, "ts": now},
    )
    fresh = await db.orders().find_one({"_id": oid})
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})

    from .orders import _serialize
    return {"order": _serialize(fresh)}
```

- [ ] **Step 4: Register router in `backend/app/main.py`**

```python
from .routers import actions, calls, orders, webhook
# ...
app.include_router(actions.router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_actions.py -v
```

Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/routers/actions.py backend/app/main.py backend/tests/test_actions.py
git commit -m "POST /api/orders/{id}/action with bucket-aware validation"
```

---

### Task 15: GET /api/stats — impact strip data

**Files:**
- Create: `backend/app/routers/stats.py`
- Modify: `backend/app/main.py` — register stats router
- Create: `backend/tests/test_stats.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_stats.py`**

```python
from datetime import datetime, timezone

import pytest


def _doc(call_status: str, bucket: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "order_id": "x", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 100,
        "call_status": call_status, "bucket": bucket, "action_state": None,
        "bolna_call_id": "x", "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


@pytest.mark.asyncio
async def test_stats_zero_when_empty(client):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["called"] == 0
    assert data["confirmed_count"] == 0
    assert data["issues_caught"] == 0
    assert data["cost_saved"] == 0


@pytest.mark.asyncio
async def test_stats_counts_correctly(client, mock_db):
    await mock_db["orders"].insert_many([
        _doc("completed", "confirmed"),
        _doc("completed", "address_updated"),
        _doc("completed", "rescheduled"),
        _doc("completed", "cancel_intent"),
        _doc("completed", "escalate"),
        _doc("pending"),
    ])
    resp = await client.get("/api/stats")
    data = resp.json()
    assert data["called"] == 5
    assert data["confirmed_count"] == 1
    assert data["issues_caught"] == 3  # address_updated + rescheduled + cancel_intent
    # Cost saved per spec formula:
    #   saved = 1.0*cancel + 0.6*addr + 0.4*resched = 1.0 + 0.6 + 0.4 = 2.0
    #   cost_saved = round(2.0 * 100) = 200
    assert data["cost_saved"] == 200
    assert data["call_spend"] == 40  # 5 * 8
    assert data["net"] == 160
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_stats.py -v
```

- [ ] **Step 3: Write `backend/app/routers/stats.py`**

```python
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
    agg = await db.orders().aggregate(pipeline).to_list(length=1)
    if not agg:
        called = confirmed = addr_u = resched = cancel = esc = 0
    else:
        a = agg[0]
        called = a["called"]
        confirmed = a["confirmed"]
        addr_u = a["address_updated"]
        resched = a["rescheduled"]
        cancel = a["cancel_intent"]
        esc = a["escalate"]
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
```

- [ ] **Step 4: Register in `backend/app/main.py`**

```python
from .routers import actions, calls, orders, stats, webhook
# ...
app.include_router(stats.router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_stats.py -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/routers/stats.py backend/app/main.py backend/tests/test_stats.py
git commit -m "GET /api/stats with bucket aggregation + ROI math"
```

---

### Task 16: Admin demo helpers — simulate-outcome, reset

**Files:**
- Create: `backend/app/routers/demo.py`
- Modify: `backend/app/main.py` — register demo router
- Create: `backend/tests/test_demo.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_demo.py`**

```python
from datetime import datetime, timezone

import pytest

from app.config import settings


def _doc(call_id: str | None = "bx") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "order_id": "X", "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "call_status": "pending", "bucket": None, "action_state": None,
        "bolna_call_id": call_id, "transcript": [], "extracted_variables": {}, "actions": [],
        "recording_url": None, "updated_address": None, "reschedule_preference": None,
        "created_at": now, "updated_at": now,
    }


@pytest.mark.asyncio
async def test_simulate_outcome_requires_admin_token(client, mock_db):
    res = await mock_db["orders"].insert_one(_doc())
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/simulate-outcome",
        json={"bucket": "confirmed"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_simulate_outcome_address_updated(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    res = await mock_db["orders"].insert_one(_doc())
    resp = await client.post(
        f"/api/orders/{res.inserted_id}/simulate-outcome",
        json={
            "bucket": "address_updated",
            "updated_address": "A-12, Koramangala 6th Block, BLR 560095",
        },
        headers={"X-Admin-Token": "secret"},
    )
    assert resp.status_code == 200
    doc = await mock_db["orders"].find_one({"_id": res.inserted_id})
    assert doc["bucket"] == "address_updated"
    assert doc["call_status"] == "completed"
    assert "Koramangala" in doc["updated_address"]
    assert len(doc["transcript"]) > 0  # synthetic transcript planted


@pytest.mark.asyncio
async def test_reset_clears_orders_and_events(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    await mock_db["orders"].insert_many([_doc("a"), _doc("b")])
    await mock_db["call_events"].insert_one({"order_id": "x", "type": "t", "source": "s", "payload": {}, "ts": datetime.now(timezone.utc)})
    resp = await client.post("/api/orders/reset", headers={"X-Admin-Token": "secret"})
    assert resp.status_code == 200
    assert (await mock_db["orders"].count_documents({})) == 0
    assert (await mock_db["call_events"].count_documents({})) == 0
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_demo.py -v
```

- [ ] **Step 3: Write `backend/app/routers/demo.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .. import db
from ..auth import require_admin_token
from ..config import settings
from ..models import Bucket
from ..pubsub import bus
from ..routers.webhook import _projection

router = APIRouter(prefix="/api/orders", tags=["demo"])


SYNTHETIC_TRANSCRIPTS = {
    "confirmed": [
        {"role": "agent", "text": "Namaste, kya main aapse baat kar rahi hoon?"},
        {"role": "customer", "text": "Haan, bolo."},
        {"role": "agent", "text": "Address aur slot confirm hai?"},
        {"role": "customer", "text": "Haan bilkul, deliver kar do."},
    ],
    "address_updated": [
        {"role": "agent", "text": "Address sahi hai ya kuch change?"},
        {"role": "customer",
         "text": "Sorry main bhai ke ghar shift ho gaya hoon, naya address bolta hoon."},
    ],
    "rescheduled": [
        {"role": "agent", "text": "Kal slot mein ghar par honge?"},
        {"role": "customer", "text": "Kal nahi, parso subah convenient hai."},
    ],
    "cancel_intent": [
        {"role": "agent", "text": "COD amount ready rakhenge?"},
        {"role": "customer", "text": "Actually mujhe yeh order cancel karna hai."},
    ],
    "escalate": [
        {"role": "agent", "text": "Confirm karein..."},
        {"role": "customer", "text": "Mujhe team se baat karni hai."},
    ],
}


class SimulateRequest(BaseModel):
    bucket: str
    updated_address: str | None = None
    reschedule_preference: str | None = None


@router.post("/{order_id}/simulate-outcome")
async def simulate_outcome(
    order_id: str,
    req: SimulateRequest,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    require_admin_token(x_admin_token, settings.admin_token)
    if req.bucket not in {b.value for b in Bucket}:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNKNOWN_BUCKET", "message": req.bucket}},
        )
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "invalid id"}},
        )
    doc = await db.orders().find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "order not found"}},
        )

    now = datetime.now(timezone.utc)
    extracted = {
        "identity_verified": True,
        "wrong_number": False,
        "address_confirmation": "updated" if req.bucket == "address_updated" else "yes",
        "availability": "reschedule" if req.bucket == "rescheduled" else "yes",
        "cod_intent": (
            "cancel" if req.bucket == "cancel_intent"
            else ("confirmed" if doc.get("payment_type") == "COD" else "na")
        ),
        "needs_human": req.bucket == "escalate",
        "updated_address": req.updated_address,
        "reschedule_preference": req.reschedule_preference,
    }
    transcript = SYNTHETIC_TRANSCRIPTS.get(req.bucket, [])
    await db.orders().update_one(
        {"_id": oid},
        {"$set": {
            "call_status": "completed",
            "bucket": req.bucket,
            "transcript": transcript,
            "extracted_variables": extracted,
            "updated_address": req.updated_address,
            "reschedule_preference": req.reschedule_preference,
            "updated_at": now,
        }},
    )
    await db.call_events().insert_one(
        {"order_id": oid, "type": "bucketed", "source": "seller",
         "payload": {"simulated": True, "bucket": req.bucket}, "ts": now},
    )
    fresh = await db.orders().find_one({"_id": oid})
    await bus.publish({"event": "order.updated", "snapshot": _projection(fresh)})
    return {"ok": True, "order_id": str(oid), "bucket": req.bucket}


@router.post("/reset")
async def reset_all(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    require_admin_token(x_admin_token, settings.admin_token)
    await db.orders().delete_many({})
    await db.call_events().delete_many({})
    await bus.publish({"event": "orders.reset"})
    return {"ok": True}
```

- [ ] **Step 4: Register in `backend/app/main.py`**

```python
from .routers import actions, calls, demo, orders, stats, webhook
# ...
app.include_router(demo.router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_demo.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/routers/demo.py backend/app/main.py backend/tests/test_demo.py
git commit -m "Admin demo helpers: simulate-outcome + reset, guarded by X-Admin-Token"
```

---

## Phase E — SSE + sweeper (Tasks 17-18)

### Task 17: GET /stream — Server-Sent Events

**Files:**
- Create: `backend/app/routers/stream.py`
- Modify: `backend/app/main.py` — register stream router
- Create: `backend/tests/test_stream.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_stream.py`**

```python
import asyncio
import json

import pytest

from app.pubsub import bus


@pytest.mark.asyncio
async def test_stream_delivers_published_events(client):
    async def publish_after_delay():
        await asyncio.sleep(0.2)
        await bus.publish({"event": "order.updated", "snapshot": {"order_id": "X"}})

    task = asyncio.create_task(publish_after_delay())
    received: list[str] = []
    async with client.stream("GET", "/stream") as resp:
        assert resp.status_code == 200
        # Read until we get one order.updated event
        async for line in resp.aiter_lines():
            received.append(line)
            joined = "\n".join(received)
            if 'order.updated' in joined and 'X' in joined:
                break
    await task
    text = "\n".join(received)
    assert "event: order.updated" in text
    assert '"order_id": "X"' in text or '"order_id":"X"' in text


@pytest.mark.asyncio
async def test_stream_sends_heartbeats(client, monkeypatch):
    from app.routers import stream as stream_module
    monkeypatch.setattr(stream_module, "HEARTBEAT_INTERVAL", 0.1)
    received: list[str] = []
    async with client.stream("GET", "/stream") as resp:
        async for line in resp.aiter_lines():
            received.append(line)
            if "heartbeat" in "\n".join(received):
                break
    assert any("heartbeat" in line for line in received)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_stream.py -v
```

- [ ] **Step 3: Write `backend/app/routers/stream.py`**

```python
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..pubsub import bus

router = APIRouter(tags=["stream"])

HEARTBEAT_INTERVAL = 15.0  # seconds


async def _event_stream():
    """SSE generator. Yields events from the pubsub bus and periodic heartbeats."""
    async with bus.subscribe() as queue:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                yield (
                    "event: heartbeat\n"
                    f"data: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"
                )
                continue
            event_name = msg.pop("event", "message")
            payload = json.dumps(msg, default=str)
            yield f"event: {event_name}\ndata: {payload}\n\n"


@router.get("/stream")
async def stream():
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx-friendly; harmless under Caddy
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 4: Register in `backend/app/main.py`**

```python
from .routers import actions, calls, demo, orders, stats, stream, webhook
# ...
app.include_router(stream.router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_stream.py -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/routers/stream.py backend/app/main.py backend/tests/test_stream.py
git commit -m "GET /stream Server-Sent Events with heartbeat"
```

---

### Task 18: Background sweeper for stuck-dialing orders

**Files:**
- Create: `backend/app/sweeper.py`
- Modify: `backend/app/main.py` — start sweeper in lifespan
- Create: `backend/tests/test_sweeper.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_sweeper.py`**

```python
from datetime import datetime, timedelta, timezone

import pytest

from app.sweeper import sweep_stuck_dialing


@pytest.mark.asyncio
async def test_sweep_marks_stuck_dialing_as_failed(mock_db):
    now = datetime.now(timezone.utc)
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
    fresh = {**stuck, "order_id": "NEW", "updated_at": now}
    await mock_db["orders"].insert_many([stuck, fresh])
    n = await sweep_stuck_dialing(threshold_minutes=5)
    assert n == 1
    old = await mock_db["orders"].find_one({"order_id": "OLD"})
    assert old["call_status"] == "failed"
    new = await mock_db["orders"].find_one({"order_id": "NEW"})
    assert new["call_status"] == "dialing"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_sweeper.py -v
```

- [ ] **Step 3: Write `backend/app/sweeper.py`**

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from . import db


async def sweep_stuck_dialing(threshold_minutes: int = 5) -> int:
    """Mark orders stuck in dialing for >threshold minutes as failed. Returns count."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    cursor = db.orders().find(
        {"call_status": "dialing", "updated_at": {"$lt": cutoff}}
    )
    stuck = await cursor.to_list(length=100)
    if not stuck:
        return 0
    ids = [d["_id"] for d in stuck]
    now = datetime.now(timezone.utc)
    await db.orders().update_many(
        {"_id": {"$in": ids}},
        {"$set": {"call_status": "failed", "updated_at": now}},
    )
    for d in stuck:
        await db.call_events().insert_one(
            {"order_id": d["_id"], "type": "error", "source": "api",
             "payload": {"reason": "dialing timeout"}, "ts": now},
        )
    return len(stuck)


async def run_periodic(interval_seconds: int = 60) -> None:
    """Long-running task: sweeps every `interval_seconds`."""
    while True:
        try:
            await sweep_stuck_dialing()
        except Exception as e:
            import logging
            logging.warning("sweeper iteration failed: %s", e)
        await asyncio.sleep(interval_seconds)
```

- [ ] **Step 4: Wire sweeper into `backend/app/main.py` lifespan**

Update the `lifespan` function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.ensure_indexes()
    import asyncio
    from .sweeper import run_periodic
    sweeper_task = asyncio.create_task(run_periodic(60))
    try:
        yield
    finally:
        sweeper_task.cancel()
        try:
            await sweeper_task
        except asyncio.CancelledError:
            pass
        await db.disconnect()
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_sweeper.py -v
```

Expected: 1 PASSED.

- [ ] **Step 6: Run all backend tests**

```bash
pytest -v
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/app/sweeper.py backend/app/main.py backend/tests/test_sweeper.py
git commit -m "Background sweeper marks stuck-dialing orders as failed"
```

---

## Phase F — Frontend foundations (Tasks 19-21)

### Task 19: Vite + React + TS + Tailwind scaffold

**Files:** all under `frontend/`

- [ ] **Step 1: Initialize Vite project**

```bash
cd "/Users/pratikyesare/Bolna Voice Agent"
cd frontend
npm create vite@latest . -- --template react-ts
# When prompted, accept overwrite
npm install
```

- [ ] **Step 2: Install Tailwind + supporting deps**

```bash
npm install -D tailwindcss@3.4 postcss autoprefixer
npm install zustand@5
npx tailwindcss init -p
```

- [ ] **Step 3: Configure `frontend/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bucket: {
          confirmed: "#10b981",
          address: "#f59e0b",
          reschedule: "#6366f1",
          cancel: "#ef4444",
          escalate: "#f97316",
        },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 4: Replace `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root {
  height: 100%;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
```

- [ ] **Step 5: Write `frontend/src/App.tsx`** (placeholder)

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 p-6">
      <h1 className="text-2xl font-semibold">Riya Console</h1>
      <p className="text-sm text-neutral-600 mt-2">Initializing…</p>
    </div>
  )
}
```

- [ ] **Step 6: Write `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 7: Configure `frontend/vite.config.ts`** to proxy backend during dev

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/webhook": "http://localhost:8000",
      "/stream": "http://localhost:8000",
    },
  },
})
```

- [ ] **Step 8: Verify dev build runs**

```bash
npm run build
```

Expected: build succeeds, `dist/` created.

- [ ] **Step 9: Commit**

```bash
cd ..
git add frontend
git commit -m "Frontend scaffold: Vite + React 19 + TS + Tailwind + Zustand"
```

---

### Task 20: Types + API client + format helpers

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/lib/format.ts`

- [ ] **Step 1: Write `frontend/src/types.ts`**

```ts
export type CallStatus = "pending" | "dialing" | "completed" | "failed" | "no_answer"
export type Bucket = "confirmed" | "address_updated" | "rescheduled" | "cancel_intent" | "escalate"
export type ActionState =
  | "dispatched"
  | "cancelled"
  | "rescheduled_confirmed"
  | "address_pushed"
  | "human_assigned"

export interface TranscriptTurn {
  role: string
  speaker_label?: string
  text: string
  ts?: string
}

export interface SellerAction {
  action: string
  note?: string | null
  by: string
  ts: string
}

export interface Order {
  _id: string
  order_id: string
  customer_name: string
  customer_phone: string
  product: string
  delivery_slot_label: string
  address: string
  pincode: string
  payment_type: "COD" | "PREPAID"
  amount: number
  call_status: CallStatus
  bolna_call_id?: string | null
  bucket?: Bucket | null
  action_state?: ActionState | null
  transcript: TranscriptTurn[]
  recording_url?: string | null
  extracted_variables: Record<string, unknown>
  updated_address?: string | null
  reschedule_preference?: string | null
  actions: SellerAction[]
  created_at: string
  updated_at: string
}

export interface UploadResponse {
  inserted: Order[]
  rejected: Array<{ row_number: number; raw: Record<string, string>; reason: string }>
  total_parsed: number
}

export interface Stats {
  called: number
  confirmed_count: number
  address_updated_count: number
  rescheduled_count: number
  cancel_intent_count: number
  escalate_count: number
  issues_caught: number
  cost_saved: number
  call_spend: number
  net: number
}

export interface OrderUpdatedEvent {
  event: "order.updated"
  snapshot: Partial<Order> & { _id: string }
}
```

- [ ] **Step 2: Write `frontend/src/api.ts`**

```ts
import type { Order, Stats, UploadResponse } from "./types"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { ...init, headers: { ...(init?.headers || {}) } })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.error?.message || `${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

export const api = {
  uploadCsv(file: File): Promise<UploadResponse> {
    const fd = new FormData()
    fd.append("file", file)
    return request<UploadResponse>("/api/orders/upload", { method: "POST", body: fd })
  },

  listOrders(filter?: { bucket?: string; call_status?: string }): Promise<{ orders: Order[] }> {
    const qs = new URLSearchParams()
    if (filter?.bucket) qs.set("bucket", filter.bucket)
    if (filter?.call_status) qs.set("call_status", filter.call_status)
    return request<{ orders: Order[] }>(`/api/orders${qs.toString() ? "?" + qs.toString() : ""}`)
  },

  getOrder(id: string): Promise<Order & { events: unknown[] }> {
    return request(`/api/orders/${id}`)
  },

  triggerCall(id: string): Promise<{ call_status: string; bolna_call_id: string }> {
    return request(`/api/orders/${id}/call`, { method: "POST" })
  },

  triggerBatch(orderIds: string[]): Promise<{ triggered: unknown[]; failed: unknown[] }> {
    return request("/api/orders/call-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_ids: orderIds }),
    })
  },

  recordAction(
    id: string,
    action: string,
    note?: string,
  ): Promise<{ order: Order }> {
    return request(`/api/orders/${id}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, note: note ?? null }),
    })
  },

  simulateOutcome(
    id: string,
    bucket: string,
    adminToken: string,
    extras?: { updated_address?: string; reschedule_preference?: string },
  ): Promise<{ ok: true }> {
    return request(`/api/orders/${id}/simulate-outcome`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Admin-Token": adminToken },
      body: JSON.stringify({ bucket, ...extras }),
    })
  },

  reset(adminToken: string): Promise<{ ok: true }> {
    return request(`/api/orders/reset`, {
      method: "POST",
      headers: { "X-Admin-Token": adminToken },
    })
  },

  stats(): Promise<Stats> {
    return request<Stats>("/api/stats")
  },
}
```

- [ ] **Step 3: Write `frontend/src/lib/format.ts`**

```ts
import type { Bucket } from "../types"

export const BUCKET_LABELS: Record<Bucket, string> = {
  confirmed: "Confirmed",
  address_updated: "Address Updated",
  rescheduled: "Rescheduled",
  cancel_intent: "Cancel Intent",
  escalate: "Escalate",
}

export const BUCKET_COLOR: Record<Bucket, string> = {
  confirmed: "bg-emerald-100 text-emerald-800 border-emerald-300",
  address_updated: "bg-amber-100 text-amber-800 border-amber-300",
  rescheduled: "bg-indigo-100 text-indigo-800 border-indigo-300",
  cancel_intent: "bg-red-100 text-red-800 border-red-300",
  escalate: "bg-orange-100 text-orange-800 border-orange-300",
}

export const BUCKET_DOT: Record<Bucket, string> = {
  confirmed: "bg-emerald-500",
  address_updated: "bg-amber-500",
  rescheduled: "bg-indigo-500",
  cancel_intent: "bg-red-500",
  escalate: "bg-orange-500",
}

export function formatINR(amount: number): string {
  return "₹" + amount.toLocaleString("en-IN")
}

export const PRIMARY_ACTION: Record<Bucket, { action: string; label: string }> = {
  confirmed: { action: "approve_dispatch", label: "Approve Dispatch" },
  address_updated: { action: "push_new_address", label: "Push New Address" },
  rescheduled: { action: "confirm_reschedule", label: "Confirm New Slot" },
  cancel_intent: { action: "cancel_dispatch", label: "Cancel Dispatch" },
  escalate: { action: "assign_human", label: "Assign to Human" },
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts frontend/src/lib/format.ts
git commit -m "Frontend types, API client, bucket format helpers"
```

---

### Task 21: Zustand store

**Files:**
- Create: `frontend/src/store.ts`

- [ ] **Step 1: Write `frontend/src/store.ts`**

```ts
import { create } from "zustand"

import type { Order, Stats } from "./types"

interface State {
  orders: Map<string, Order>
  stats: Stats | null
  connState: "connected" | "reconnecting" | "disconnected"
  filterBucket: string | null
  drawerOrderId: string | null

  setOrders(list: Order[]): void
  upsertOrder(partial: Partial<Order> & { _id: string }): void
  removeOrder(id: string): void
  clearOrders(): void
  setStats(s: Stats): void
  setConnState(s: State["connState"]): void
  setFilterBucket(b: string | null): void
  setDrawerOrderId(id: string | null): void
}

export const useStore = create<State>((set) => ({
  orders: new Map(),
  stats: null,
  connState: "disconnected",
  filterBucket: null,
  drawerOrderId: null,

  setOrders(list) {
    const m = new Map<string, Order>()
    for (const o of list) m.set(o._id, o)
    set({ orders: m })
  },

  upsertOrder(partial) {
    set((st) => {
      const m = new Map(st.orders)
      const existing = m.get(partial._id)
      m.set(partial._id, { ...(existing ?? ({} as Order)), ...(partial as Order) })
      return { orders: m }
    })
  },

  removeOrder(id) {
    set((st) => {
      const m = new Map(st.orders)
      m.delete(id)
      return { orders: m }
    })
  },

  clearOrders() {
    set({ orders: new Map() })
  },

  setStats(s) {
    set({ stats: s })
  },

  setConnState(s) {
    set({ connState: s })
  },

  setFilterBucket(b) {
    set({ filterBucket: b })
  },

  setDrawerOrderId(id) {
    set({ drawerOrderId: id })
  },
}))
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store.ts
git commit -m "Zustand store with order Map, filter, drawer state"
```

---

## Phase G — Frontend components (Tasks 22-29)

### Task 22: TopBar component

**Files:**
- Create: `frontend/src/components/TopBar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/components/TopBar.tsx`**

```tsx
interface Props {
  brand: string
  onUploadClick: () => void
  onDemoClick: () => void
}

export function TopBar({ brand, onUploadClick, onDemoClick }: Props) {
  return (
    <header className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-semibold">{brand}</span>
        <span className="text-neutral-400">•</span>
        <span className="text-sm font-medium text-neutral-600">Riya Console</span>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={onUploadClick}
          className="rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-neutral-700"
        >
          Upload CSV
        </button>
        <button
          onClick={onDemoClick}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-100"
        >
          ⚙ Demo ▾
        </button>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: Modify `frontend/src/App.tsx`** to use it

```tsx
import { useState } from "react"
import { TopBar } from "./components/TopBar"

export default function App() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [demoOpen, setDemoOpen] = useState(false)
  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <TopBar
        brand="Snitch"
        onUploadClick={() => setUploadOpen(true)}
        onDemoClick={() => setDemoOpen((v) => !v)}
      />
      <main className="px-6 py-4">
        {uploadOpen && <p className="text-sm">Upload modal placeholder</p>}
        {demoOpen && <p className="text-sm">Demo menu placeholder</p>}
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build && cd ..
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TopBar.tsx frontend/src/App.tsx
git commit -m "TopBar component with upload + demo controls"
```

---

### Task 23: UploadModal component + CSV upload

**Files:**
- Create: `frontend/src/components/UploadModal.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/components/UploadModal.tsx`**

```tsx
import { useState } from "react"
import { api } from "../api"
import { useStore } from "../store"

interface Props {
  open: boolean
  onClose: () => void
}

export function UploadModal({ open, onClose }: Props) {
  const upsertOrder = useStore((s) => s.upsertOrder)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejected, setRejected] = useState<
    Array<{ row_number: number; reason: string }>
  >([])

  if (!open) return null

  async function handleFile(file: File) {
    setBusy(true)
    setError(null)
    setRejected([])
    try {
      const res = await api.uploadCsv(file)
      for (const o of res.inserted) upsertOrder(o)
      setRejected(res.rejected.map((r) => ({ row_number: r.row_number, reason: r.reason })))
      if (res.rejected.length === 0) onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="w-[480px] rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Upload orders CSV</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-900">
            ×
          </button>
        </div>
        <label className="block cursor-pointer rounded-md border-2 border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-600 hover:border-neutral-400">
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void handleFile(f)
            }}
          />
          Drop a CSV here or click to browse.
        </label>
        {busy && <p className="mt-3 text-sm">Uploading…</p>}
        {error && (
          <p className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>
        )}
        {rejected.length > 0 && (
          <div className="mt-3 rounded bg-amber-50 p-2 text-sm text-amber-800">
            <div className="font-medium">
              {rejected.length} row{rejected.length === 1 ? "" : "s"} rejected:
            </div>
            <ul className="ml-4 list-disc">
              {rejected.map((r) => (
                <li key={r.row_number}>
                  Row {r.row_number}: {r.reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Modify `frontend/src/App.tsx`**

```tsx
import { useState } from "react"
import { TopBar } from "./components/TopBar"
import { UploadModal } from "./components/UploadModal"

export default function App() {
  const [uploadOpen, setUploadOpen] = useState(false)
  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <TopBar brand="Snitch" onUploadClick={() => setUploadOpen(true)} onDemoClick={() => {}} />
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  )
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build && cd ..
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UploadModal.tsx frontend/src/App.tsx
git commit -m "UploadModal: CSV upload with per-row error display"
```

---

### Task 24: OrderTable + OrderRow with bucket badge

**Files:**
- Create: `frontend/src/components/OrderRow.tsx`
- Create: `frontend/src/components/OrderTable.tsx`
- Modify: `frontend/src/App.tsx` — render table, load on mount

- [ ] **Step 1: Write `frontend/src/components/OrderRow.tsx`**

```tsx
import { useState } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_COLOR, BUCKET_DOT, BUCKET_LABELS, PRIMARY_ACTION } from "../lib/format"
import type { Bucket, Order } from "../types"

interface Props {
  order: Order
}

export function OrderRow({ order }: Props) {
  const setDrawerOrderId = useStore((s) => s.setDrawerOrderId)
  const upsertOrder = useStore((s) => s.upsertOrder)
  const [busy, setBusy] = useState(false)

  async function onTrigger(e: React.MouseEvent) {
    e.stopPropagation()
    setBusy(true)
    try {
      const res = await api.triggerCall(order._id)
      upsertOrder({ _id: order._id, ...res } as Partial<Order> & { _id: string })
    } finally {
      setBusy(false)
    }
  }

  async function onPrimaryAction(e: React.MouseEvent) {
    e.stopPropagation()
    if (!order.bucket) return
    const a = PRIMARY_ACTION[order.bucket as Bucket]
    setBusy(true)
    try {
      const res = await api.recordAction(order._id, a.action)
      upsertOrder(res.order)
    } finally {
      setBusy(false)
    }
  }

  const bucket = order.bucket as Bucket | null

  return (
    <tr
      onClick={() => setDrawerOrderId(order._id)}
      className="cursor-pointer border-b border-neutral-100 transition-colors hover:bg-neutral-50"
    >
      <td className="px-4 py-3 text-sm">{order.order_id}</td>
      <td className="px-4 py-3 text-sm">{order.customer_name}</td>
      <td className="px-4 py-3 text-sm">
        {order.call_status === "dialing" && <span>⟳ Dialing…</span>}
        {order.call_status === "completed" && <span>✓ Completed</span>}
        {order.call_status === "pending" && <span className="text-neutral-500">— Pending</span>}
        {order.call_status === "failed" && <span className="text-red-600">✗ Failed</span>}
        {order.call_status === "no_answer" && <span className="text-neutral-500">No answer</span>}
      </td>
      <td className="px-4 py-3 text-sm">
        {bucket ? (
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${BUCKET_COLOR[bucket]}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${BUCKET_DOT[bucket]}`} />
            {BUCKET_LABELS[bucket]}
          </span>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right text-sm">
        {order.call_status === "pending" && (
          <button
            disabled={busy}
            onClick={onTrigger}
            className="rounded-md border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-100 disabled:opacity-50"
          >
            Trigger call
          </button>
        )}
        {bucket && order.action_state == null && (
          <button
            disabled={busy}
            onClick={onPrimaryAction}
            className="rounded-md bg-neutral-900 px-2 py-1 text-xs font-medium text-white hover:bg-neutral-700 disabled:opacity-50"
          >
            {PRIMARY_ACTION[bucket].label}
          </button>
        )}
        {order.action_state && (
          <span className="text-xs text-neutral-500">✓ {order.action_state}</span>
        )}
      </td>
    </tr>
  )
}
```

- [ ] **Step 2: Write `frontend/src/components/OrderTable.tsx`**

```tsx
import { useMemo } from "react"
import { useStore } from "../store"
import { OrderRow } from "./OrderRow"

export function OrderTable() {
  const orders = useStore((s) => s.orders)
  const filterBucket = useStore((s) => s.filterBucket)

  const rows = useMemo(() => {
    const arr = Array.from(orders.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
    if (!filterBucket) return arr
    return arr.filter((o) => o.bucket === filterBucket)
  }, [orders, filterBucket])

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 bg-white p-12 text-center text-sm text-neutral-500">
        No orders yet. Upload a CSV to get started.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
      <table className="w-full text-left">
        <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
          <tr>
            <th className="px-4 py-2">Order</th>
            <th className="px-4 py-2">Customer</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Outcome</th>
            <th className="px-4 py-2 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <OrderRow key={o._id} order={o} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: Modify `frontend/src/App.tsx`** to load orders on mount

```tsx
import { useEffect, useState } from "react"
import { api } from "./api"
import { useStore } from "./store"
import { TopBar } from "./components/TopBar"
import { UploadModal } from "./components/UploadModal"
import { OrderTable } from "./components/OrderTable"

export default function App() {
  const setOrders = useStore((s) => s.setOrders)
  const [uploadOpen, setUploadOpen] = useState(false)

  useEffect(() => {
    void api.listOrders().then((r) => setOrders(r.orders))
  }, [setOrders])

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <TopBar brand="Snitch" onUploadClick={() => setUploadOpen(true)} onDemoClick={() => {}} />
      <main className="px-6 py-4 space-y-4">
        <OrderTable />
      </main>
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  )
}
```

- [ ] **Step 4: Build and commit**

```bash
cd frontend && npm run build && cd ..
git add frontend/src/components/OrderRow.tsx frontend/src/components/OrderTable.tsx frontend/src/App.tsx
git commit -m "OrderTable + OrderRow with bucket badge and primary action"
```

---

### Task 25: BucketTabs filter chips

**Files:**
- Create: `frontend/src/components/BucketTabs.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/components/BucketTabs.tsx`**

```tsx
import { useMemo } from "react"
import { useStore } from "../store"
import { BUCKET_LABELS } from "../lib/format"
import type { Bucket } from "../types"

const BUCKETS: Bucket[] = ["confirmed", "address_updated", "rescheduled", "cancel_intent", "escalate"]

export function BucketTabs() {
  const orders = useStore((s) => s.orders)
  const filterBucket = useStore((s) => s.filterBucket)
  const setFilterBucket = useStore((s) => s.setFilterBucket)

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: 0 }
    for (const b of BUCKETS) c[b] = 0
    for (const o of orders.values()) {
      c.all += 1
      if (o.bucket) c[o.bucket] = (c[o.bucket] ?? 0) + 1
    }
    return c
  }, [orders])

  function Tab({ id, label }: { id: string | null; label: string }) {
    const isActive = filterBucket === id || (id === null && filterBucket === null)
    return (
      <button
        onClick={() => setFilterBucket(id)}
        className={
          "rounded-full border px-3 py-1 text-xs font-medium transition " +
          (isActive
            ? "border-neutral-900 bg-neutral-900 text-white"
            : "border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50")
        }
      >
        {label} {id === null ? counts.all : (counts[id] ?? 0)}
      </button>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      <Tab id={null} label="All" />
      {BUCKETS.map((b) => (
        <Tab key={b} id={b} label={BUCKET_LABELS[b]} />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Add to `frontend/src/App.tsx`** above the table

```tsx
import { BucketTabs } from "./components/BucketTabs"
// in JSX, inside <main>:
<BucketTabs />
<OrderTable />
```

- [ ] **Step 3: Build and commit**

```bash
cd frontend && npm run build && cd ..
git add frontend/src/components/BucketTabs.tsx frontend/src/App.tsx
git commit -m "BucketTabs filter chips with live counts"
```

---

### Task 26: OrderDrawer with transcript + actions + events

**Files:**
- Create: `frontend/src/components/OrderDrawer.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/components/OrderDrawer.tsx`**

```tsx
import { useEffect, useState } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_COLOR, BUCKET_LABELS, PRIMARY_ACTION, formatINR } from "../lib/format"
import type { Bucket, Order } from "../types"

export function OrderDrawer() {
  const drawerOrderId = useStore((s) => s.drawerOrderId)
  const setDrawerOrderId = useStore((s) => s.setDrawerOrderId)
  const upsertOrder = useStore((s) => s.upsertOrder)
  const orderFromStore = useStore((s) =>
    s.drawerOrderId ? s.orders.get(s.drawerOrderId) : undefined,
  )
  const [detail, setDetail] = useState<(Order & { events: unknown[] }) | null>(null)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!drawerOrderId) {
      setDetail(null)
      return
    }
    void api.getOrder(drawerOrderId).then(setDetail)
  }, [drawerOrderId])

  if (!drawerOrderId) return null
  const o = detail ?? (orderFromStore as Order | undefined)
  if (!o) {
    return (
      <aside className="fixed right-0 top-0 z-30 h-full w-[60%] overflow-y-auto border-l border-neutral-200 bg-white p-6 shadow-xl">
        Loading…
      </aside>
    )
  }

  const bucket = o.bucket as Bucket | null

  async function runAction(actionKey: string) {
    setBusy(true)
    try {
      const res = await api.recordAction(o!._id, actionKey, note || undefined)
      upsertOrder(res.order)
      setDetail({ ...(o as Order), ...res.order, events: detail?.events ?? [] })
      setNote("")
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="fixed right-0 top-0 z-30 h-full w-[60%] overflow-y-auto border-l border-neutral-200 bg-white p-6 shadow-xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-neutral-500">
            Order {o.order_id}
          </div>
          <h2 className="text-xl font-semibold">{o.customer_name}</h2>
          <p className="text-sm text-neutral-600">{o.customer_phone}</p>
        </div>
        <button
          onClick={() => setDrawerOrderId(null)}
          className="text-neutral-500 hover:text-neutral-900"
        >
          ×
        </button>
      </div>

      <section className="mt-5 grid grid-cols-2 gap-y-1 gap-x-6 text-sm">
        <div className="text-neutral-500">Product</div>
        <div>{o.product}</div>
        <div className="text-neutral-500">Slot</div>
        <div>{o.delivery_slot_label}</div>
        <div className="text-neutral-500">Address</div>
        <div>{o.address}</div>
        <div className="text-neutral-500">Payment</div>
        <div>
          {o.payment_type} {formatINR(o.amount)}
        </div>
      </section>

      {bucket && (
        <section className="mt-5">
          <div
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${BUCKET_COLOR[bucket]}`}
          >
            {BUCKET_LABELS[bucket]}
          </div>
          {o.updated_address && (
            <div className="mt-2 rounded bg-amber-50 p-2 text-sm">
              <span className="font-medium">New address: </span>
              {o.updated_address}
            </div>
          )}
          {o.reschedule_preference && (
            <div className="mt-2 rounded bg-indigo-50 p-2 text-sm">
              <span className="font-medium">Reschedule pref: </span>
              {o.reschedule_preference}
            </div>
          )}
        </section>
      )}

      {o.recording_url && (
        <section className="mt-5">
          <a
            href={o.recording_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-blue-700 underline"
          >
            ▶ Play recording
          </a>
        </section>
      )}

      <section className="mt-5">
        <h3 className="text-sm font-semibold text-neutral-700">Transcript</h3>
        <div className="mt-2 max-h-56 overflow-y-auto rounded border border-neutral-200 p-3 text-sm">
          {o.transcript.length === 0 && (
            <p className="text-neutral-500">No transcript yet.</p>
          )}
          {o.transcript.map((t, i) => (
            <p key={i} className="mb-1">
              <span className="font-medium">{t.role === "agent" ? "Riya" : t.speaker_label || o.customer_name}: </span>
              {t.text}
            </p>
          ))}
        </div>
      </section>

      {bucket && o.action_state == null && (
        <section className="mt-5">
          <h3 className="text-sm font-semibold text-neutral-700">Action</h3>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional note…"
            className="mt-2 w-full rounded border border-neutral-300 p-2 text-sm"
            rows={2}
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              disabled={busy}
              onClick={() => runAction(PRIMARY_ACTION[bucket].action)}
              className="rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-neutral-700 disabled:opacity-50"
            >
              {PRIMARY_ACTION[bucket].label}
            </button>
            <button
              disabled={busy}
              onClick={() => runAction("cancel_dispatch")}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50"
            >
              Cancel dispatch
            </button>
            <button
              disabled={busy}
              onClick={() => runAction("assign_human")}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50"
            >
              Assign human
            </button>
          </div>
        </section>
      )}

      {o.action_state && (
        <section className="mt-5">
          <div className="rounded bg-emerald-50 p-2 text-sm text-emerald-800">
            Action recorded: <span className="font-medium">{o.action_state}</span>
          </div>
        </section>
      )}
    </aside>
  )
}
```

- [ ] **Step 2: Add to `frontend/src/App.tsx`**

```tsx
import { OrderDrawer } from "./components/OrderDrawer"
// in JSX after <UploadModal>:
<OrderDrawer />
```

- [ ] **Step 3: Build and commit**

```bash
cd frontend && npm run build && cd ..
git add frontend/src/components/OrderDrawer.tsx frontend/src/App.tsx
git commit -m "OrderDrawer with transcript, recording link, and per-bucket action buttons"
```

---

### Task 27: ImpactStrip

**Files:**
- Create: `frontend/src/components/ImpactStrip.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/components/ImpactStrip.tsx`**

```tsx
import { useEffect } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { formatINR } from "../lib/format"

export function ImpactStrip() {
  const stats = useStore((s) => s.stats)
  const setStats = useStore((s) => s.setStats)
  const orders = useStore((s) => s.orders)

  useEffect(() => {
    void api.stats().then(setStats)
  }, [orders, setStats])

  if (!stats) return null
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm">
      <div className="font-medium text-neutral-700">Impact (today)</div>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-neutral-700">
        <span>
          Called: <strong>{stats.called}</strong>
        </span>
        <span>
          Confirmed: <strong>{stats.confirmed_count}</strong>
        </span>
        <span>
          Issues caught early: <strong>{stats.issues_caught}</strong>
        </span>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-4 text-neutral-700">
        <span>
          Est. RTO cost saved: <strong>{formatINR(stats.cost_saved)}</strong>
        </span>
        <span>
          Call spend: <strong>{formatINR(stats.call_spend)}</strong>
        </span>
        <span className={stats.net >= 0 ? "text-emerald-700" : "text-red-700"}>
          Net: <strong>{(stats.net >= 0 ? "+" : "") + formatINR(stats.net)}</strong>
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add to `frontend/src/App.tsx`** above BucketTabs

- [ ] **Step 3: Build and commit**

```bash
cd frontend && npm run build && cd ..
git add frontend/src/components/ImpactStrip.tsx frontend/src/App.tsx
git commit -m "ImpactStrip showing called counts + ROI math"
```

---

### Task 28: SSE hookup + ConnectionDot + reconnect

**Files:**
- Create: `frontend/src/sse.ts`
- Create: `frontend/src/components/ConnectionDot.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/sse.ts`**

```ts
import { api } from "./api"
import { useStore } from "./store"

let source: EventSource | null = null

export function connectStream() {
  const store = useStore.getState()
  if (source) source.close()
  store.setConnState("disconnected")
  source = new EventSource("/stream")

  source.onopen = () => {
    useStore.getState().setConnState("connected")
    // On reconnect, re-sync orders.
    void api.listOrders().then((r) => useStore.getState().setOrders(r.orders))
    void api.stats().then((s) => useStore.getState().setStats(s))
  }

  source.addEventListener("order.updated", (ev) => {
    const data = JSON.parse((ev as MessageEvent).data) as {
      snapshot: { _id: string; [k: string]: unknown }
    }
    useStore.getState().upsertOrder(data.snapshot as { _id: string })
    void api.stats().then((s) => useStore.getState().setStats(s))
  })

  source.addEventListener("orders.reset", () => {
    useStore.getState().clearOrders()
    void api.stats().then((s) => useStore.getState().setStats(s))
  })

  source.onerror = () => {
    useStore.getState().setConnState("reconnecting")
    // EventSource auto-reconnects; nothing else to do.
  }
}
```

- [ ] **Step 2: Write `frontend/src/components/ConnectionDot.tsx`**

```tsx
import { useStore } from "../store"

export function ConnectionDot() {
  const state = useStore((s) => s.connState)
  const dot =
    state === "connected"
      ? "bg-emerald-500"
      : state === "reconnecting"
      ? "bg-amber-500"
      : "bg-neutral-400"
  const label =
    state === "connected"
      ? "live • connected via SSE"
      : state === "reconnecting"
      ? "reconnecting…"
      : "disconnected"
  return (
    <div className="flex items-center gap-2 text-xs text-neutral-500">
      <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
      <span>{label}</span>
    </div>
  )
}
```

- [ ] **Step 3: Wire into `frontend/src/App.tsx`**

```tsx
import { useEffect } from "react"
import { connectStream } from "./sse"
import { ConnectionDot } from "./components/ConnectionDot"
// inside App component:
useEffect(() => { connectStream() }, [])
// inside JSX <main>:
<ConnectionDot />
```

- [ ] **Step 4: Build and commit**

```bash
cd frontend && npm run build && cd ..
git add frontend/src/sse.ts frontend/src/components/ConnectionDot.tsx frontend/src/App.tsx
git commit -m "SSE wiring + ConnectionDot for live order/stats updates"
```

---

### Task 29: DemoControlsMenu

**Files:**
- Create: `frontend/src/components/DemoControlsMenu.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/components/DemoControlsMenu.tsx`**

```tsx
import { useState } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_LABELS } from "../lib/format"
import type { Bucket, Order } from "../types"

interface Props {
  open: boolean
  onClose: () => void
}

const BUCKETS: Bucket[] = ["confirmed", "address_updated", "rescheduled", "cancel_intent", "escalate"]

export function DemoControlsMenu({ open, onClose }: Props) {
  const orders = useStore((s) => s.orders)
  const clearOrders = useStore((s) => s.clearOrders)
  const [adminToken, setAdminToken] = useState(() => localStorage.getItem("adminToken") ?? "")
  const [targetId, setTargetId] = useState("")
  const [bucket, setBucket] = useState<Bucket>("address_updated")
  const [updatedAddress, setUpdatedAddress] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  function saveToken(t: string) {
    setAdminToken(t)
    localStorage.setItem("adminToken", t)
  }

  async function onSimulate() {
    if (!targetId || !adminToken) {
      setError("Pick an order and provide admin token")
      return
    }
    setBusy(true)
    setError(null)
    try {
      await api.simulateOutcome(targetId, bucket, adminToken, {
        updated_address: updatedAddress || undefined,
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulate failed")
    } finally {
      setBusy(false)
    }
  }

  async function onTriggerAll() {
    setBusy(true)
    try {
      const ids = Array.from(orders.values())
        .filter((o) => o.call_status === "pending")
        .map((o) => o._id)
      if (ids.length === 0) return
      await api.triggerBatch(ids)
    } finally {
      setBusy(false)
    }
  }

  async function onReset() {
    if (!adminToken) {
      setError("Provide admin token")
      return
    }
    setBusy(true)
    try {
      await api.reset(adminToken)
      clearOrders()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reset failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="absolute right-6 top-16 z-40 w-[360px] rounded-md border border-neutral-200 bg-white p-4 shadow-xl">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Demo controls</h3>
        <button onClick={onClose} className="text-neutral-500">×</button>
      </div>
      <div className="mt-3 space-y-2 text-sm">
        <label className="block">
          Admin token
          <input
            type="password"
            value={adminToken}
            onChange={(e) => saveToken(e.target.value)}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          />
        </label>
        <div className="border-t border-neutral-100 pt-3">
          <div className="text-xs font-medium uppercase text-neutral-500">Simulate outcome</div>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          >
            <option value="">— Pick order —</option>
            {Array.from(orders.values() as Iterable<Order>).map((o) => (
              <option key={o._id} value={o._id}>
                {o.order_id} — {o.customer_name}
              </option>
            ))}
          </select>
          <select
            value={bucket}
            onChange={(e) => setBucket(e.target.value as Bucket)}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          >
            {BUCKETS.map((b) => (
              <option key={b} value={b}>{BUCKET_LABELS[b]}</option>
            ))}
          </select>
          {bucket === "address_updated" && (
            <input
              value={updatedAddress}
              onChange={(e) => setUpdatedAddress(e.target.value)}
              placeholder="New address (verbatim)"
              className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
            />
          )}
          <button
            disabled={busy}
            onClick={onSimulate}
            className="mt-2 w-full rounded bg-neutral-900 px-2 py-1 text-sm text-white disabled:opacity-50"
          >
            Simulate
          </button>
        </div>
        <div className="border-t border-neutral-100 pt-3 flex gap-2">
          <button
            disabled={busy}
            onClick={onTriggerAll}
            className="flex-1 rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-50"
          >
            Trigger all pending
          </button>
          <button
            disabled={busy}
            onClick={onReset}
            className="flex-1 rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
          >
            Reset all
          </button>
        </div>
        {error && <div className="text-xs text-red-700">{error}</div>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire into `frontend/src/App.tsx`**

```tsx
import { useState, useEffect } from "react"
import { DemoControlsMenu } from "./components/DemoControlsMenu"
// inside App:
const [demoOpen, setDemoOpen] = useState(false)
// pass to TopBar:
<TopBar brand="Snitch" onUploadClick={() => setUploadOpen(true)} onDemoClick={() => setDemoOpen((v) => !v)} />
// in JSX:
<DemoControlsMenu open={demoOpen} onClose={() => setDemoOpen(false)} />
```

- [ ] **Step 3: Build and commit**

```bash
cd frontend && npm run build && cd ..
git add frontend/src/components/DemoControlsMenu.tsx frontend/src/App.tsx
git commit -m "DemoControlsMenu: simulate outcome, trigger all pending, reset"
```

---

## Phase H — Deployment artifacts (Tasks 30-34)

### Task 30: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

- [ ] **Step 2: Write `backend/.dockerignore`**

```
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
tests/
.env
*.pyc
```

- [ ] **Step 3: Local build check**

```bash
cd backend && docker build -t riya-api:dev . && cd ..
```

Expected: image builds successfully.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "Backend Dockerfile (Python 3.12, single Uvicorn worker)"
```

---

### Task 31: Frontend Dockerfile (multi-stage build)

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`

- [ ] **Step 1: Write `frontend/Dockerfile`**

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

# Final stage just exposes /app/dist as a volume artifact; the Caddy
# container is what actually serves the files (it mounts ../frontend/dist).
# We keep this image around for build verification in CI; in compose,
# we build directly on the host and mount the dist/ dir into Caddy.
FROM alpine:3.20
COPY --from=build /app/dist /dist
CMD ["sh", "-c", "echo 'frontend build artifact at /dist'"]
```

- [ ] **Step 2: Write `frontend/.dockerignore`**

```
node_modules/
dist/
.git/
```

- [ ] **Step 3: Local build check**

```bash
cd frontend && docker build -t riya-web:dev . && cd ..
```

- [ ] **Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/.dockerignore
git commit -m "Frontend multi-stage Dockerfile (Node 22 build → artifact image)"
```

---

### Task 32: docker-compose.yml + Caddyfile

**Files:**
- Create: `docker-compose.yml`
- Create: `Caddyfile`

- [ ] **Step 1: Write `Caddyfile`** (at repo root)

```
{$DOMAIN} {
    encode gzip

    @api path /api/* /webhook/*
    handle @api {
        reverse_proxy api:8000
    }

    handle /stream {
        reverse_proxy api:8000 {
            flush_interval -1
            transport http {
                read_timeout 0
            }
        }
    }

    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
```

- [ ] **Step 2: Write `docker-compose.yml`** (at repo root)

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - DOMAIN=${DOMAIN}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./frontend/dist:/srv:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api

  api:
    build: ./backend
    restart: unless-stopped
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - MONGODB_DB=${MONGODB_DB}
      - BOLNA_API_KEY=${BOLNA_API_KEY}
      - BOLNA_AGENT_ID=${BOLNA_AGENT_ID}
      - BOLNA_WEBHOOK_SECRET=${BOLNA_WEBHOOK_SECRET}
      - BOLNA_BASE_URL=${BOLNA_BASE_URL:-https://api.bolna.dev}
      - ADMIN_TOKEN=${ADMIN_TOKEN}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL}

volumes:
  caddy_data:
  caddy_config:
```

- [ ] **Step 3: Local sanity check**

```bash
docker compose config
```

Expected: prints resolved config without errors.

- [ ] **Step 4: Commit**

```bash
git add Caddyfile docker-compose.yml
git commit -m "Caddy + FastAPI Docker Compose stack with SSE-friendly reverse-proxy"
```

---

### Task 33: deploy.sh helper script

**Files:**
- Create: `deploy.sh`

- [ ] **Step 1: Write `deploy.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Convenience deploy script: pull, build frontend, rebuild containers.
# Run on the EC2 host from the repo root.

echo "==> git pull"
git pull --ff-only

echo "==> Build frontend"
docker run --rm \
  -v "$(pwd)/frontend":/app \
  -w /app \
  node:22-alpine \
  sh -c "npm ci || npm install; npm run build"

echo "==> Rebuild and restart compose"
docker compose up -d --build

echo "==> Health check"
sleep 3
curl -sf http://localhost/health || curl -sf "https://${DOMAIN:-localhost}/health" || true

echo "Done."
```

- [ ] **Step 2: Make executable + commit**

```bash
chmod +x deploy.sh
git add deploy.sh
git commit -m "deploy.sh: pull, build frontend in container, recompose"
```

---

### Task 34: README + EC2 setup runbook

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Riya — Pre-Delivery Confirmation Voice Agent

Hinglish voice agent + seller ops console that runs outbound confirmation
calls before delivery to reduce RTO (Return-to-Origin) on Indian D2C orders.

- Use case + design: [docs/superpowers/specs/2026-05-11-bolna-rto-confirmation-agent-design.md](docs/superpowers/specs/2026-05-11-bolna-rto-confirmation-agent-design.md)
- Implementation plan: [docs/superpowers/plans/2026-05-11-bolna-rto-confirmation-agent.md](docs/superpowers/plans/2026-05-11-bolna-rto-confirmation-agent.md)
- Voice agent prompt + variable schema: [docs/bolna-agent-prompt.md](docs/bolna-agent-prompt.md)

## Architecture

- Caddy (TLS, static, reverse-proxy with SSE flushing) on one EC2 host
- FastAPI single-worker process (REST + Bolna webhook + SSE pubsub)
- MongoDB Atlas M0 (Mumbai)
- React + Vite frontend, served as static files by Caddy

## Local development

Backend:
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Frontend:
```
cd frontend
npm install
npm run dev   # proxies /api, /webhook, /stream to localhost:8000
```

Run tests:
```
cd backend && pytest -v
```

## Deployment (EC2 + Docker Compose, ap-south-1)

### One-time host setup

1. Launch EC2 `t3.small` Ubuntu 24.04 LTS in `ap-south-1`.
2. Attach an Elastic IP.
3. Security group: 80/443 from `0.0.0.0/0`, 22 from your IP.
4. Install Docker + Compose:
```
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
```
5. Point your DNS A-record (e.g., `riya.example.com`) at the Elastic IP.
6. Allowlist the Elastic IP in MongoDB Atlas → Network Access.

### Deploy

```
git clone <repo-url> && cd <repo>
cp .env.example .env       # edit with real values
./deploy.sh
```

Visit `https://${DOMAIN}` to use the console.

## Environment variables

See [.env.example](.env.example).

## Endpoints

- `POST /api/orders/upload` — multipart CSV
- `GET  /api/orders` — list with filters
- `GET  /api/orders/{id}` — full doc + events
- `POST /api/orders/{id}/call` — trigger Bolna call
- `POST /api/orders/call-batch` — bulk trigger
- `POST /api/orders/{id}/action` — record seller action
- `POST /api/orders/{id}/simulate-outcome` — admin-only demo helper
- `POST /api/orders/reset` — admin-only demo helper
- `POST /webhook/bolna` — Bolna outcome receiver (HMAC-verified)
- `GET  /api/stats` — impact strip data
- `GET  /stream` — Server-Sent Events
- `GET  /health` — health check

## Bolna agent setup

See [docs/bolna-agent-prompt.md](docs/bolna-agent-prompt.md) for the canonical
Riya prompt, variable-in/extracted-out schema, and the Bolna dashboard
configuration checklist.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "README with architecture overview and EC2 deploy runbook"
```

---

## Phase I — CI, Bolna agent config, demo artifacts (Tasks 35-37)

### Task 35: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e '.[dev]'
      - name: Lint
        run: ruff check app tests
      - name: Test
        run: pytest -v

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install
        run: npm ci || npm install
      - name: Type check
        run: npx tsc --noEmit
      - name: Build
        run: npm run build
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "CI: lint + pytest backend, tsc + build frontend"
```

---

### Task 36: Bolna agent prompt document (manual config reference)

**Files:**
- Create: `docs/bolna-agent-prompt.md`

- [ ] **Step 1: Write `docs/bolna-agent-prompt.md`**

```markdown
# Riya — Bolna agent configuration

This is the canonical configuration you paste into the Bolna dashboard when
creating the "Riya" agent. The seller console assumes the agent extracts
the variables listed in §3 below.

## 1. Agent system prompt

> You are Riya, a delivery confirmation agent calling on behalf of
> **{brand_name}**. You speak primarily in **Hinglish** — natural
> Hindi-English mixing as urban Indian customers actually speak (e.g.,
> "address confirm kar lein", "kal subah deliver hoga"). Switch to fluent
> English only if the customer responds in English for two consecutive
> turns. Always be warm, brief, respectful. Never pushy, robotic, or
> English-academic. Max call length 3 minutes. If anything goes off-script
> or the customer is upset, exit politely and set `needs_human = true`.

## 2. Initial message (spoken on connect)

> Namaste, kya main **{customer_name}** se baat kar rahi hoon? Main Riya
> hoon, **{brand_name}** se. Aapke order **{order_id}** ke baare mein ek
> chhota confirmation tha — bas do minute.

## 3. Conversation graph

### Step 1 — Identity verification
"Pehle confirm kar lein — aap **{customer_name}** hi hain na?"
- Confirmed → proceed
- Wrong person → set `wrong_number=true`, end politely
- Hesitant → cite `{order_id}` once more

### Step 2 — Address confirmation
"Aapka order **{delivery_slot_label}** ko deliver hoga, address par:
**{address_short}**. Yeh sahi hai, ya kuch change karna hai?"
- Confirmed → `address_confirmation="yes"`
- Wants change → "Naya address bataaiye" → capture full text into
  `updated_address`, set `address_confirmation="updated"`

### Step 3 — Availability
"Bahut accha. **{delivery_slot_label}** ko ghar par honge?"
- Yes → `availability="yes"`
- No → "Kab convenient hai — kal subah, kal shaam, ya parso?" → capture
  `reschedule_preference` (enum) + `reschedule_preference_text`

### Step 4 — COD intent (only if `payment_type == "COD"`)
"Order COD hai, **₹{amount}** ka. Delivery ke time amount ready
rakhenge?"
- Yes → `cod_intent="confirmed"`
- Cancel → `cod_intent="cancel"`
- Hesitant once more → `needs_human=true`
- For PREPAID: skip; set `cod_intent="na"`

### Closing
"Bahut accha, aapka time dene ke liye dhanyavaad! Aapka order time par
pahunch jaayega. Have a great day!"

### Edge cases
- Customer busy → "Main thodi der baad call karoon?" → `needs_human=true`
- Customer angry / out-of-domain question → polite exit + `needs_human=true`
- 8s of silence / voicemail → Bolna marks `call_status="no_answer"`

## 4. Variables passed IN (request body to Bolna `POST /v2/calls`)

```json
{
  "customer_name": "Ananya Sharma",
  "brand_name": "Snitch",
  "order_id": "SNT-2026-051142",
  "product": "Snitch Oversized Tee — Olive — L",
  "delivery_slot_label": "kal subah 10 baje se 1 baje tak",
  "address_short": "B-204, Indiranagar, Bengaluru",
  "payment_type": "COD",
  "amount": 1499
}
```

## 5. Variables extracted OUT (Bolna dashboard structured output config)

| Variable                       | Type    | Notes                                                  |
|--------------------------------|---------|--------------------------------------------------------|
| `identity_verified`            | boolean | Step 1 yes branch                                      |
| `wrong_number`                 | boolean | Step 1 wrong-person branch                             |
| `address_confirmation`         | enum    | `"yes"` \| `"updated"` \| `"not_confirmed"`            |
| `updated_address`              | string  | Verbatim if changed; else null                         |
| `availability`                 | enum    | `"yes"` \| `"reschedule"` \| `"not_confirmed"`         |
| `reschedule_preference`        | enum    | `"kal_subah"` \| `"kal_shaam"` \| `"parso"` \| `"other"` \| `null` |
| `reschedule_preference_text`   | string  | Verbatim free text                                     |
| `cod_intent`                   | enum    | `"confirmed"` \| `"cancel"` \| `"na"`                  |
| `needs_human`                  | boolean | Hostility, confusion, hesitation                       |
| `call_summary`                 | string  | One-line summary                                       |

## 6. Bolna dashboard checklist

- [ ] Create agent "Riya" with the above prompt and initial message
- [ ] Voice: Indian female (closest natural Hinglish preset)
- [ ] Max call duration: 180s
- [ ] Recording: ON
- [ ] Filler/backchannel: ON
- [ ] Configure extracted-variables schema per §5
- [ ] Set webhook URL: `https://${DOMAIN}/webhook/bolna`
- [ ] If HMAC signing is offered: copy secret into `BOLNA_WEBHOOK_SECRET`
- [ ] Copy `agent_id` into `BOLNA_AGENT_ID`
- [ ] Copy API key into `BOLNA_API_KEY`
- [ ] Top up demo credits (3-5 calls' worth)

## 7. Open questions to confirm against Bolna docs

1. Exact field name for `agent_id` in create-call body — code accepts
   `agent_id`; adjust `app/bolna.py` if Bolna uses a different key.
2. Webhook payload shape — code defensively extracts `call_id`/`callId`/`id`,
   `transcript`, `recording_url`, `extracted_variables`. Confirm field
   names from the dry-run.
3. Whether `transcript` is a list of turns or a flat string. If flat,
   adjust `_projection` and the OrderDrawer transcript rendering.
4. HMAC header name — code reads `X-Bolna-Signature`; adjust in
   `app/routers/webhook.py` if Bolna uses a different header.
```

- [ ] **Step 2: Commit**

```bash
git add docs/bolna-agent-prompt.md
git commit -m "Bolna agent prompt + extracted-variable schema + dashboard checklist"
```

---

### Task 37: Demo CSV + dry-run checklist

**Files:**
- Create: `scripts/demo_orders.csv`
- Create: `docs/dry-run-checklist.md`

- [ ] **Step 1: Write `scripts/demo_orders.csv`**

Replace `+91XXXXXXXXXX` in Row 1 with your real phone for the dry-run; placeholder phones in Rows 2-3 are fine because those rows get simulated outcomes.

```csv
order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount
SNT-2026-051142,Ananya Sharma,+91XXXXXXXXXX,Snitch Oversized Tee Olive L,kal subah 10 baje se 1 baje tak,"B-204, Prestige Acropolis, Indiranagar, Bengaluru, KA",560038,COD,1499
SNT-2026-051143,Rohit Mehra,+919999900001,Snitch Cargo Trouser Black 32,kal shaam 4 baje se 7 baje tak,"C-12, Whitefield, Bengaluru, KA",560066,PREPAID,2299
SNT-2026-051144,Priya Nair,+919999900002,Snitch Hooded Sweatshirt Grey M,parso subah 9 baje se 12 baje tak,"A-7, Banjara Hills Road 12, Hyderabad, TS",500034,COD,1799
```

- [ ] **Step 2: Write `docs/dry-run-checklist.md`**

```markdown
# Dry-run checklist (the night before recording)

## 1. Sanity-check the deployment

- [ ] `curl https://${DOMAIN}/health` returns 200
- [ ] `curl https://${DOMAIN}/api/version` returns version string
- [ ] EC2 elastic IP is allowlisted in MongoDB Atlas Network Access
- [ ] Open `https://${DOMAIN}` — dashboard loads, ConnectionDot shows green

## 2. Verify Bolna agent and webhook

- [ ] In Bolna dashboard, confirm agent "Riya" is configured per
  [docs/bolna-agent-prompt.md](bolna-agent-prompt.md)
- [ ] Webhook URL on the Bolna agent points to `https://${DOMAIN}/webhook/bolna`
- [ ] `BOLNA_API_KEY`, `BOLNA_AGENT_ID`, `BOLNA_WEBHOOK_SECRET` are set in
  `.env` and the api container has been restarted to pick them up
- [ ] Account has at least 5 calls of credit

## 3. End-to-end dry-run on Row 1

- [ ] In the dashboard, click **⚙ Demo ▾** → enter `ADMIN_TOKEN`
- [ ] Click **Reset all** so the dashboard is clean
- [ ] Click **Upload CSV** → upload `scripts/demo_orders.csv` with your real
  phone in Row 1
- [ ] Confirm 3 rows appear as `pending`
- [ ] Click **Trigger call** on Row 1; your phone should ring within 10s
- [ ] Run the full 4-step conversation: identity → address (say "yes") →
  availability (say "yes") → COD intent (say "haan, ready hai")
- [ ] After hang-up, Row 1 should flip to `confirmed` within ~30s
- [ ] Open Row 1 drawer; confirm transcript and recording link are present
- [ ] If recording link is publicly playable, great. If not, note it for
  the deck — we'll have to embed the captured audio file instead.

## 4. Capture a Plan B fallback

- [ ] Screen-capture Row 1's transcript and (if available) recording so we
  have a Plan B if the live call fails on recording day
- [ ] Save the captured `.mp3` to `assets/dry-run-row1.mp3` (gitignored)

## 5. Verify simulate-outcome works on Rows 2 and 3

- [ ] In Demo controls: simulate Row 2 → `address_updated` with the
  verbatim text:
  > "Sorry, abhi main bhai ke ghar shift ho gaya hoon — A-12, Koramangala
  > 6th Block, BLR 560095, near KFC"
- [ ] Row 2 should flash and bucket to `Address Updated`
- [ ] Open Row 2 drawer; click **Push New Address**; row shows
  `action_state: address_pushed`
- [ ] Simulate Row 3 → `cancel_intent`
- [ ] Row 3 should bucket to `Cancel Intent`
- [ ] Open Row 3 drawer; click **Cancel Dispatch**; row shows `cancelled`
- [ ] Check ImpactStrip: ROI math should reflect saved cost

## 6. Reset for the real recording

- [ ] Click **Reset all** so the recording starts with an empty dashboard
- [ ] Practice the 5-7 min recording arc once cold

## 7. Recording day morning

- [ ] Recheck `curl https://${DOMAIN}/health`
- [ ] Recheck Bolna account credit
- [ ] Make sure your phone is on Indian network with good reception
- [ ] Turn on do-not-disturb except for the test call
- [ ] Start recording at full screen, dashboard open, empty
```

- [ ] **Step 3: Commit**

```bash
git add scripts/demo_orders.csv docs/dry-run-checklist.md
git commit -m "Demo CSV + dry-run checklist for recording day"
```

---

## Final verification (Task 38)

### Task 38: End-to-end smoke test

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && pytest -v && cd ..
```

Expected: all tests green.

- [ ] **Step 2: Run ruff lint**

```bash
cd backend && ruff check app tests && cd ..
```

Expected: no errors.

- [ ] **Step 3: TypeScript type check + build**

```bash
cd frontend && npx tsc --noEmit && npm run build && cd ..
```

Expected: no TS errors; build succeeds.

- [ ] **Step 4: Smoke-test the local stack**

```bash
# Backend in one terminal:
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Frontend in another:
cd frontend && npm run dev

# Visit http://localhost:5173 — dashboard loads, ConnectionDot green,
# Upload CSV works, simulate-outcome works (use ADMIN_TOKEN=dev-admin-token).
```

- [ ] **Step 5: Verify CI passes**

Push to GitHub and confirm both `backend` and `frontend` workflow jobs go green.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit --allow-empty -m "Riya MVP feature complete; dry-run ready"
```

---

## Spec coverage map

| Spec section                              | Tasks covering it                                  |
|-------------------------------------------|----------------------------------------------------|
| §3 Architecture (Caddy + FastAPI + Mongo) | 2, 3, 30, 31, 32                                   |
| §3 Data flow (canonical path)             | 5, 9-14, 17                                        |
| §4 `orders` collection + indexes          | 3, 4, 9                                            |
| §4 `call_events` collection               | 3, 9, 11, 13, 14                                   |
| §4 Bucket classification rules            | 6                                                  |
| §4 CSV schema                             | 5                                                  |
| §5 Riya prompt + initial message          | 36                                                 |
| §5 Conversation graph + variables IN/OUT  | 36                                                 |
| §5 Edge cases                             | 36                                                 |
| §5 Bolna dashboard config                 | 36                                                 |
| §6 Orders upload/list/get                 | 9, 10                                              |
| §6 Call orchestration + batch             | 11                                                 |
| §6 Bolna webhook + HMAC + idempotency     | 7, 13                                              |
| §6 Seller action endpoint                 | 14                                                 |
| §6 Demo helpers (simulate, reset)         | 16                                                 |
| §6 SSE stream                             | 12, 17                                             |
| §6 Stats endpoint                         | 15                                                 |
| §6 Auth model (HMAC + admin token)        | 7, 13, 16                                          |
| §6 Error model                            | 9, 10, 11, 13, 14, 16                              |
| §7 UI layout + components                 | 19-29                                              |
| §7 Bucket → row-action map                | 14, 20, 24, 26                                     |
| §7 SSE wiring + reconnect                 | 28                                                 |
| §7 Impact strip formula                   | 15, 27                                             |
| §7 Zustand store                          | 21                                                 |
| §8 EC2 + Docker Compose stack             | 30, 31, 32, 33, 34                                 |
| §8 Caddyfile (SSE flush)                  | 32                                                 |
| §8 Secrets via `.env`                     | 1, 34                                              |
| §8 MongoDB Atlas (manual)                 | 34 (README runbook)                                |
| §9 Demo CSV + dry-run script              | 37                                                 |
| §9 Recording arc                          | 37                                                 |
| §9 Plan B/C fallback                      | 37                                                 |
| §10 Error handling matrix                 | 9, 11, 13, 14, 16                                  |
| §10 Webhook idempotency                   | 13                                                 |
| §10 Stuck-dialing sweeper                 | 18                                                 |
| §11 CSV/classifier/HMAC/E2E tests         | 5, 6, 7, 13                                        |
| §11 CI: ruff + pytest                     | 35                                                 |
| §12 Risk register (mitigations)           | 13 (defensive webhook), 18 (sweeper), 37 (Plan B)  |
| §13 Out of scope                          | Acknowledged via omission                          |
| §14 Open questions                        | 36 (§7)                                            |


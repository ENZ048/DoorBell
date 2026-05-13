# Doorbell

**Pre-delivery confirmation platform for Indian D2C brands.** Catches the addresses, availability gaps, and COD second-thoughts that turn into RTO — before the courier leaves the hub.

A Hinglish voice agent ("Riya") calls every customer a couple of hours before their delivery slot, runs a structured four-step check, and classifies the outcome into one of five buckets the seller acts on inside a real-time dashboard.

> **Live demo:** [doorbell.chatroute.in](https://doorbell.chatroute.in) · **API:** [doorbell-api.chatroute.in/health](https://doorbell-api.chatroute.in/health)
>
> Built for the Bolna Full-Stack Engineer assignment, May 2026.

---

## The problem in one paragraph

In Indian e-commerce, 20–30% of orders fail on the first delivery attempt — wrong address, customer not home, buyer's remorse on cash-on-delivery. Each failed delivery costs the brand roughly ₹80–150 in forward + reverse logistics, plus inventory liquidity hit. None of it is visible until the courier is already at the doorstep.

Doorbell catches the recoverable share **before dispatch**. A confirmation call costs ₹8. A saved RTO is worth ~₹100. ROI: 10–15× per saved order.

---

## What it does

**Riya** (the voice agent) calls the customer 2–4 hours before their delivery slot and runs a 4-step structured check:

| Step | What Riya verifies |
|---|---|
| 1. Identity | "Am I speaking with {customer_name}?" |
| 2. Address  | "Address: {address} — still correct?" |
| 3. Availability | "Will you be home during {delivery_slot}?" |
| 4. COD intent (COD only) | "Please keep ₹{amount} ready. Is that okay?" |

The structured outcome lands as one of **five buckets**:

| Bucket | Trigger | Seller action |
|---|---|---|
| 🟢 Confirmed | All four checks pass | Approve dispatch |
| 🟡 Address updated | Customer gave a new address | Push new address to courier |
| 🟣 Rescheduled | Customer wants a different slot | Confirm new slot |
| 🔴 Cancel intent | Customer wants to cancel (COD) | Cancel dispatch |
| 🟠 Escalate | Anything off-script | Assign to human |

---

## Features

- **CSV ingestion** with per-row validation (Indian phone normalization, payment-type enum, partial success)
- **Live outbound calling** via Bolna's voice API
- **5-bucket outcome classifier** with deterministic priority rules
- **Real-time dashboard** — orders flip state without page refresh (Server-Sent Events)
- **Per-row primary action** with bucket-aware validation (can't push a new address on a "Confirmed" order)
- **Bulk actions** — "Call all pending" and per-bucket "Approve all"
- **Inline audio player** for call recordings (play in drawer, no nav-away)
- **One-click recording download** via backend proxy
- **AI-generated call summary** in the drawer for at-a-glance triage
- **Full transcript** + **event timeline** per order
- **Impact KPI tiles** — Calls today, Confirmed, Issues caught, Net ₹ saved (live ROI math)
- **No-answer detection** from Bolna's hangup reason (rings into a separate state, not a false escalate)
- **Stuck-dialing sweeper** — background task marks orders failed after 5 min of unanswered dialing
- **HMAC-verified webhook** ingress with idempotency on duplicate deliveries
- **Production-ready deploy** — TLS via Caddy + Let's Encrypt on a single EC2 instance

---

## Architecture

```
                          ┌───────────────────────────────────────────────┐
                          │  EC2 t3.small (ap-south-1, Mumbai)            │
                          │                                               │
   Customer's browser ───▶│  Caddy :443     ┌────────────────────────┐    │
   (doorbell.*)           │  ├─ /          │ frontend/dist (React)  │    │
                          │  │              │ served as static files │    │
                          │  └─ /api/*      └────────────────────────┘    │
                          │     /webhook/*                                │
                          │     /stream      ┌────────────────────────┐   │
   Bolna webhook ────────▶│      ↓           │  FastAPI :8000         │   │
   (doorbell-api.*)       │      └──────────▶│  uvicorn (1 worker)    │   │
                          │                  │  REST + webhook + SSE  │   │
                          │                  │  in-proc pubsub        │   │
                          │                  └─────────┬──────────────┘   │
                          │                            │                  │
                          └────────────────────────────┼──────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ MongoDB Atlas   │
                                              │  M0, Mumbai     │
                                              └─────────────────┘
                                                       ▲
                                                       │ outbound
                          ┌────────────────────────────┴──────────────────┐
                          │ Bolna (voice agent platform)                  │
                          │  • LLM: GPT-4.1-mini                          │
                          │  • TTS: ElevenLabs Turbo v2.5 (Hinglish)      │
                          │  • Transcriber: Deepgram Nova-3               │
                          │  • Telephony: Plivo                           │
                          └───────────────────────────────────────────────┘
```

**Why single-box:** the entire stack fits in ~500 MB RAM on a `t3.small`. Two subdomains (`doorbell.*` for the dashboard, `doorbell-api.*` for the API) share Caddy's TLS termination; Caddy routes by hostname. SSE flushing is explicit (`flush_interval -1`) so the live event stream isn't buffered.

---

## Tech stack

### Backend
- **Python 3.12** · **FastAPI** 0.118 · **Uvicorn** (1 worker for in-process SSE pubsub)
- **Motor** 3.6 (async MongoDB driver) · **Pydantic v2** for models and settings
- **httpx** for Bolna API + recording-download proxy
- **pytest** 8.3 + **mongomock-motor** + **respx** — 85+ tests, all green

### Frontend
- **React 19** · **TypeScript 5.6** · **Vite 6** (~240 kB JS, ~73 kB gzipped)
- **Tailwind 3.4** (custom `ink` neutrals + `brand-secondary` teal `#11b993`)
- **Zustand 5** for client state, **lucide-react** for icons
- **Geist Sans / Geist Mono** typography (cv11, ss03, ss04 features enabled)
- Custom audio player, drawer with three-tab navigation, real-time row animations via SSE

### Infrastructure
- **Caddy 2-alpine** — auto Let's Encrypt, reverse proxy, static file server, SSE-friendly
- **Docker Compose** on a single **EC2 t3.small** in `ap-south-1` (Mumbai)
- **MongoDB Atlas M0** (free tier, Mumbai region)
- **Hostinger** DNS for `chatroute.in`
- **GitHub Actions** CI (ruff + pytest backend, tsc + vite build frontend)

### Voice / telephony
- **Bolna** as the voice-agent platform — agent prompt, extractions, webhook orchestration
- **ElevenLabs Turbo v2.5** for Hinglish TTS
- **Deepgram Nova-3** for transcription
- **Plivo** as Bolna's telephony provider

---

## Live URLs

| Surface | URL |
|---|---|
| Dashboard | https://doorbell.chatroute.in |
| API health | https://doorbell-api.chatroute.in/health |
| Sample CSV | https://doorbell.chatroute.in/sample-orders.csv |

---

## Project documents

| Doc | What's inside |
|---|---|
| [docs/superpowers/specs/2026-05-11-bolna-rto-confirmation-agent-design.md](docs/superpowers/specs/2026-05-11-bolna-rto-confirmation-agent-design.md) | Full design spec — problem framing, architecture, data model, agent design, API surface, deployment topology, error handling, risk register |
| [docs/superpowers/plans/2026-05-11-bolna-rto-confirmation-agent.md](docs/superpowers/plans/2026-05-11-bolna-rto-confirmation-agent.md) | 38-task implementation plan, broken down TDD-first with full test code and impl code per task |
| [docs/bolna-agent-prompt.md](docs/bolna-agent-prompt.md) | Canonical Riya prompt, variable schema (in + out), Bolna dashboard config checklist |
| [docs/deploy-runbook.md](docs/deploy-runbook.md) | Step-by-step EC2 + DNS + Atlas + Bolna deploy walkthrough with troubleshooting matrix |
| [docs/dry-run-checklist.md](docs/dry-run-checklist.md) | Pre-recording checklist for the demo video |

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Requires a `.env` in the repo root (copy from `.env.example` and fill in MongoDB Atlas URI + Bolna credentials).

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api /webhook /stream to :8000
```

### Tests

```bash
cd backend && pytest -v        # 85 tests, ~0.3s
cd frontend && npx tsc --noEmit && npm run build
```

---

## Deployment

See [docs/deploy-runbook.md](docs/deploy-runbook.md) for the complete walkthrough. Quick version:

```bash
# On a fresh EC2 (Ubuntu 24.04+):
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker

git clone https://github.com/ENZ048/DoorBell.git doorbell
cd doorbell
cp .env.example .env       # fill in MONGODB_URI, BOLNA_*, ADMIN_TOKEN, domains
./deploy.sh
```

Caddy issues TLS certs on first boot. Point `DOMAIN_WEB` and `DOMAIN_API` A-records at your Elastic IP and the certs land within seconds.

---

## API surface

```
POST  /api/orders/upload                 multipart CSV ingestion
GET   /api/orders                        list (filter by call_status, bucket, action_state)
GET   /api/orders/{id}                   full doc + last 20 call events
POST  /api/orders/{id}/call              trigger one Bolna call
POST  /api/orders/call-batch             trigger N calls in parallel (semaphored)
POST  /api/orders/{id}/action            seller action (validated per bucket)
GET   /api/orders/{id}/recording         stream-proxy MP3 with Content-Disposition: attachment

POST  /webhook/bolna                     Bolna outcome receiver (HMAC-verified, idempotent)

GET   /api/stats                         live impact-strip math
GET   /stream                            Server-Sent Events for dashboard live updates
GET   /health                            health check (mongo connectivity)

POST  /api/orders/{id}/simulate-outcome  admin-only (X-Admin-Token)
POST  /api/orders/reset                  admin-only (X-Admin-Token) — wipes orders + events
```

---

## Engineering notes worth calling out

- **Webhook payload flattener** — Bolna's actual webhook nests extracted fields three levels deep (`extracted_data.RTO.{field}.{objective|subjective}`). The classifier needs flat keys. A defensive flattener handles the real shape *and* the simulated shape, preferring `objective` (pre-defined picks) over `subjective` (free-text fallback).
- **No-answer detection** — empty `extracted_data` after a real call usually means the customer never picked up. Without explicit detection, the classifier's fallback rule would mark it as `escalate`, which is misleading. Doorbell looks at `telephony_data.hangup_reason` for signals like `no_answer`, `busy`, `voicemail`, `machine_detection` and sets `call_status="no_answer"` *without* running the bucket classifier.
- **Status-aware webhook ingestion** — Bolna fires webhooks on both call initiation (`status: initiated`, empty data) and completion. Without a status guard the initiation payload would write `escalate` and the completion payload would skip via the idempotency check. Doorbell only classifies on `completed`, `error`, `rejected`, or `cancelled`.
- **Partial-filter unique index** on `bolna_call_id` — MongoDB's `sparse` only excludes documents where the field is *missing*. New orders are inserted with `bolna_call_id: null` *present*, so sparse fails them on duplicate `null`s. A `partialFilterExpression: { bolna_call_id: { $type: "string" } }` index enforces uniqueness only when actually populated.
- **SSE + Caddy + httpx** — three different layers each needed their own coaxing. Caddy needs `flush_interval -1`; FastAPI runs single-worker so the in-process pubsub fans out cleanly; the SSE test suite exercises `_event_stream()` directly because `httpx.ASGITransport` buffers the entire response body before returning (incompatible with infinite streams).
- **Cross-origin downloads** — the audio file is on Bolna's S3, which sends `Content-Type: audio/mpeg` but no `Content-Disposition`. Browsers ignore the HTML `download` attribute for cross-origin URLs without that header, so the download click would open a new tab instead of saving. Doorbell adds a same-origin proxy endpoint that streams the file with the right headers, so the browser actually saves the MP3.

---

## Repository structure

```
.
├── README.md                            this file
├── .env.example                         env-var template
├── Caddyfile                            two-vhost reverse proxy + static
├── docker-compose.yml                   caddy + api services
├── deploy.sh                            one-shot deploy script
├── .github/workflows/ci.yml             ruff + pytest + tsc + vite-build
│
├── backend/
│   ├── Dockerfile                       python:3.12-slim
│   ├── pyproject.toml                   deps pinned
│   ├── app/
│   │   ├── main.py                      FastAPI factory + CORS + lifespan
│   │   ├── config.py                    pydantic-settings
│   │   ├── db.py                        Motor client + partial-filter index
│   │   ├── models.py                    Order, CallEvent, enums
│   │   ├── csv_parser.py                CSV → Order with per-row validation
│   │   ├── classifier.py                deterministic 5-bucket rules
│   │   ├── bolna.py                     Bolna API client
│   │   ├── auth.py                      HMAC + admin token verification
│   │   ├── pubsub.py                    in-process asyncio fan-out
│   │   ├── sweeper.py                   stuck-dialing background task
│   │   └── routers/                     orders, calls, webhook, actions, stats, stream, demo
│   └── tests/                           85+ tests
│
├── frontend/
│   ├── Dockerfile                       node:22-alpine build stage
│   ├── index.html
│   ├── package.json
│   ├── public/                          favicon, sample-orders.csv
│   └── src/
│       ├── App.tsx                      page shell
│       ├── types.ts                     mirrors backend models
│       ├── api.ts                       fetch wrappers (uses VITE_API_BASE_URL)
│       ├── sse.ts                       EventSource hookup
│       ├── store.ts                     Zustand
│       ├── lib/format.ts                bucket labels, colors, primary actions
│       └── components/                  TopBar, ImpactStrip, BucketTabs,
│                                        OrderTable, OrderRow, OrderDrawer,
│                                        UploadModal, AudioPlayer, ConnectionDot
│
├── docs/
│   ├── bolna-agent-prompt.md
│   ├── deploy-runbook.md
│   ├── dry-run-checklist.md
│   └── superpowers/
│       ├── specs/2026-05-11-bolna-rto-confirmation-agent-design.md
│       └── plans/2026-05-11-bolna-rto-confirmation-agent.md
│
└── scripts/
    └── demo_orders.csv
```

---

## Built by

**Pratik Yesare** — Full-Stack Developer at [Troika Tech](https://troikatech.in), Mumbai.

Submitted as the Full-Stack Engineer assignment for [Bolna](https://bolna.ai), May 2026.

Repo: [github.com/ENZ048/DoorBell](https://github.com/ENZ048/DoorBell)

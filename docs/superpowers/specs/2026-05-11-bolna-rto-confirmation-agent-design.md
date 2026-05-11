# Riya — Pre-Delivery Confirmation Voice Agent

**Spec date:** 2026-05-11
**Status:** Approved for implementation planning
**Author:** Bolna Full-Stack Assignment build
**Time budget:** 2-day wall-clock window; assignment guideline is 7 hrs of active build (2hr agent + 4hr web app + 1hr demo)

---

## 1. Executive summary

**Problem.** Indian D2C / e-commerce brands lose 20-30% of orders to RTO (Return-to-Origin) — each failed first-attempt delivery costs ~₹80-150 in forward + reverse logistics plus inventory liquidity hit. COD orders fail materially more often than prepaid. The largest, most-recoverable share of these failures is preventable: wrong address, customer not home during the slot, impulse-COD remorse. None of that is visible until the courier reaches the doorstep.

**Solution.** A Hinglish voice agent ("Riya") runs an outbound confirmation call 2-4 hrs before the scheduled delivery slot. The call runs a structured 4-step check — identity → address → availability → COD intent — and returns a classified outcome the seller acts on before dispatch leaves the hub.

**Outcome metric (primary).** Absolute RTO % drop on called orders vs an uncalled control cohort. Target: 30-50% relative reduction in first-attempt failures. Per-order ROI: call ~₹8, saved failed delivery ~₹100 midpoint → 10-15× ROI per saved order.

**Secondary metrics.** Delivery confirmation rate, cost-per-saved-RTO, cancel-intent capture rate (COD-only), human-handoff rate.

**Deliverables for the assignment.**
- Bolna voice agent ("Riya") configured with structured prompt + extracted-variable schema + webhook target
- Web app (FastAPI + React) — seller ops console
- Deployed on EC2 (Mumbai region) behind Caddy, MongoDB Atlas free tier
- 5-7 min screen recording of full E2E flow
- GitHub repo + deployed public link

---

## 2. Use case — operational detail

**Industry.** Indian D2C / e-commerce, last-mile logistics. Reference brand profiles: beauty (Mamaearth), fashion (Snitch), marketplace sellers, daily volume 500-5,000 orders.

**Caller.** The D2C brand or seller, calling automatically when an order moves to "Out for Delivery" status in their OMS or shipping aggregator (Shiprocket / Delhivery / Ecom Express).

**Callee.** End customer who placed the order — Tier 1, 2, 3 cities — Hinglish primary, English fallback.

**Workflow (production-shaped).**

1. Order ships → OMS status flips to "Out for Delivery" → webhook to backend.
2. Backend queues a Bolna call with structured variables (customer name, order ID, product, delivery slot, address, payment type, amount).
3. Riya places the call, runs the 4-step structured check, returns a structured outcome + transcript via webhook.
4. Backend classifies into one of 5 bucket states: `confirmed`, `address_updated`, `rescheduled`, `cancel_intent`, `escalate`.
5. Seller dashboard surfaces each bucket and primary action; seller acts (approve dispatch / push new address / confirm reschedule / cancel dispatch / assign human).

**Workflow (build-shaped for this assignment).** Same flow, with CSV upload standing in for the OMS webhook trigger. Real Bolna call for the demo hero order; pre-staged synthetic outcomes for two additional rows to demonstrate the breadth of buckets in a single short recording.

---

## 3. System architecture

### Components (all on one EC2 instance, ap-south-1, in Docker Compose)

- **`caddy`** — Caddy 2 in a single container. Terminates TLS via auto-Let's-Encrypt, serves the React build at `/`, reverse-proxies `/api/*`, `/webhook/*`, and `/stream` to FastAPI. SSE-aware (`flush_interval -1`).
- **`api`** — FastAPI on Uvicorn, single worker. Houses REST endpoints, Bolna webhook receiver, SSE stream, in-process asyncio pub-sub fan-out for live updates.
- **MongoDB Atlas (M0 free tier, Mumbai region)** — `orders` and `call_events` collections. Connection via env var. EC2 elastic IP allowlisted on Atlas.
- **Bolna (external)** — places outbound calls; POSTs back to our webhook on call end.

### Single-worker SSE constraint

In-process pubsub fan-out only works in one Uvicorn worker, so we run `--workers 1`. This is fine for the demo. If horizontal scale is ever required, the migration path is Redis pub/sub. Explicitly out of scope here.

### Data flow (canonical path)

```
1. Seller uploads orders.csv      → POST /api/orders/upload (multipart)
                                     → FastAPI parses, validates, inserts N order docs
                                       with call_status=pending

2. Seller clicks "Trigger calls"   → POST /api/orders/{id}/call
                                     → FastAPI POSTs Bolna /v2/calls with agent_id +
                                       recipient_phone + variables
                                     → marks order dialing, stores bolna_call_id
                                     → fan-out "order.updated" → SSE

3. Bolna runs Riya call            → external, ~60-120s

4. Bolna posts outcome             → POST /webhook/bolna
                                     → verify HMAC, match call_id to order
                                     → extract transcript + variables
                                     → run bucket classifier
                                     → write order + append call_events
                                     → fan-out "order.updated" → SSE

5. Dashboard updates live          → React EventSource on /stream merges snapshot
                                     → row animates from dialing → completed → bucket

6. Seller acts on row              → POST /api/orders/{id}/action
                                     → append actions[] + set action_state
                                     → fan-out → SSE → row reflects resolution
```

No queue, no Celery, no Redis. Bolna calls are non-blocking (we fire-and-forget the create-call POST and wait for the webhook).

---

## 4. Data model (MongoDB)

### `orders` (one document per CSV row)

```js
{
  _id: ObjectId,
  order_id: "SNT-2026-051142",          // brand's external order ID
  customer_name: "Ananya Sharma",
  customer_phone: "+919876543210",       // E.164, normalized on ingest
  product: "Snitch Oversized Tee — Olive — L",
  delivery_slot: "2026-05-12T10:00:00+05:30/13:00:00+05:30",
  delivery_slot_label: "kal subah 10 se 1 baje tak",  // Hinglish-rendered for Bolna variable
  address: "B-204, Prestige Acropolis, 100 Ft Road, Indiranagar, Bengaluru, KA",
  pincode: "560038",
  payment_type: "COD",                   // "COD" | "PREPAID"
  amount: 1499,                          // INR rupees, integer

  // Lifecycle
  call_status: "pending",                // pending | dialing | completed | failed | no_answer
  bolna_call_id: null,                   // set after POST /v2/calls
  bucket: null,                          // set after classification
  action_state: null,                    // set after seller acts

  // Outcome (populated by webhook)
  transcript: [],                        // [{role, speaker_label, text, ts}]
  recording_url: null,
  extracted_variables: {},               // raw structured outcome from Bolna
  updated_address: null,                 // if address_confirmation=="updated"
  reschedule_preference: null,           // enum if availability=="reschedule"

  actions: [],                           // append-only: [{action, note, by, ts}]

  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:** `{bolna_call_id: 1}` unique-sparse (webhook matching); `{created_at: -1}` (dashboard listing); `{bucket: 1}` (filter).

### `call_events` (append-only audit trail)

```js
{
  _id: ObjectId,
  order_id: ObjectId,
  type: "created" | "call_initiated" | "webhook_received"
      | "bucketed" | "action_taken" | "error",
  source: "csv" | "api" | "bolna" | "seller",
  payload: { /* raw — full Bolna body for webhook_received, action data for action_taken, etc. */ },
  ts: ISODate
}
```

**Index:** `{order_id: 1, ts: 1}`.

### Bucket classification (deterministic; first match wins)

Run on the `extracted_variables` payload after webhook lands:

| Condition                                            | Bucket            |
|------------------------------------------------------|-------------------|
| `needs_human == true` OR call had an error flag      | `escalate`        |
| `cod_intent == "cancel"` (only when `payment_type=="COD"`) | `cancel_intent`   |
| `address_confirmation == "updated"`                  | `address_updated` |
| `availability == "reschedule"`                       | `rescheduled`     |
| Identity verified + address confirmed + available + (COD intent confirmed if COD) | `confirmed`       |

Compound cases (e.g., new address AND new slot) classify to the most-actionable single bucket per priority above; transcript carries both signals; the row action covers the combined update.

### CSV schema

Required headers (case-insensitive): `order_id, customer_name, customer_phone, product, delivery_slot_label, address, pincode, payment_type, amount`. Phone normalized to E.164 on parse (reject + report per-row errors if invalid). Valid rows insert as `pending`.

---

## 5. Riya — voice agent design

### Identity & language stance (agent system prompt)

> "You are Riya, a delivery confirmation agent calling on behalf of **{brand_name}**. You speak primarily in **Hinglish** — natural Hindi-English mixing as urban Indian customers actually speak (e.g., 'address confirm kar lein', 'kal subah deliver hoga'). Switch to fluent English only if the customer responds in English for two consecutive turns. Always be warm, brief, respectful. Never pushy, robotic, or English-academic. Max call length 3 minutes. If anything goes off-script or the customer is upset, exit politely and set `needs_human = true`."

### Initial message (Bolna says this on connect)

> "Namaste, kya main **{customer_name}** se baat kar rahi hoon? Main Riya hoon, **{brand_name}** se. Aapke order **{order_id}** ke baare mein ek chhota confirmation tha — bas do minute."

### Conversation graph — 4 structured steps

**Step 1 — Identity verification**
- "Pehle confirm kar lein — aap **{customer_name}** hi hain na?"
- Confirmed → proceed
- Wrong person → mark `wrong_number=true`, polite exit
- Hesitant → cite `{order_id}` for context, ask once more

**Step 2 — Address confirmation**
- "Aapka order **{delivery_slot_label}** ko deliver hoga, address par: **{address_short}**. Yeh sahi hai, ya kuch change karna hai?"
- Confirmed → `address_confirmation="yes"`
- Wants change → "Naya address bataaiye" → capture `updated_address`, set `address_confirmation="updated"`

**Step 3 — Availability**
- "Bahut accha. **{delivery_slot_label}** ko ghar par honge?"
- Yes → `availability="yes"`
- No → "Kab convenient hai — kal subah, kal shaam, ya parso?" → capture `reschedule_preference` (enum) + `reschedule_preference_text` (verbatim free text)

**Step 4 — COD intent (conditional; only if `payment_type=="COD"`)**
- "Order COD hai, **₹{amount}** ka. Delivery ke time amount ready rakhenge?"
- Yes → `cod_intent="confirmed"`
- Cancel → `cod_intent="cancel"`
- Hesitant → ask once more → still hesitant → `needs_human=true`
- Skipped for PREPAID → set `cod_intent="na"`

**Closing:** "Bahut accha, aapka time dene ke liye dhanyavaad! Aapka order time par pahunch jaayega. Have a great day!"

### Variables passed IN (Bolna create-call request body)

`customer_name`, `brand_name`, `order_id`, `product`, `delivery_slot_label` (pre-rendered Hinglish, e.g., "kal subah 10 baje se 1 baje tak"), `address_short` (first line + locality, voice-friendly), `payment_type`, `amount`.

### Variables extracted OUT (Bolna agent's structured outcome config)

| Variable                       | Type    | Notes                                                     |
|--------------------------------|---------|-----------------------------------------------------------|
| `identity_verified`            | boolean | Step 1 yes branch                                         |
| `wrong_number`                 | boolean | Step 1 wrong-person branch                                |
| `address_confirmation`         | enum    | `"yes" | "updated" | "not_confirmed"`                  |
| `updated_address`              | string? | Verbatim if changed; else null                            |
| `availability`                 | enum    | `"yes" | "reschedule" | "not_confirmed"`               |
| `reschedule_preference`        | enum    | `"kal_subah" | "kal_shaam" | "parso" | "other" | null`  |
| `reschedule_preference_text`   | string? | Verbatim free text                                        |
| `cod_intent`                   | enum    | `"confirmed" | "cancel" | "na"`                        |
| `needs_human`                  | boolean | Hostility, confusion, hesitation after retry              |
| `call_summary`                 | string  | Agent-generated one-liner                                 |

### Edge cases handled in-prompt

- **Customer busy** → "Koi baat nahi, main thodi der baad call karoon?" → `needs_human=true` (operator decides retry).
- **Customer angry** → "Aapki feedback important hai, main team se confirm karwati hoon" → polite exit, `needs_human=true`.
- **Out-of-domain question** → "Iske liye team contact karwati hoon" → `needs_human=true`.
- **Voicemail / DTMF / no human voice 8s** → Bolna call_status flips to `no_answer`; backend marks order accordingly, no bucket set.

### Bolna dashboard config

- Voice: Indian female (Bolna's most natural Hinglish preset)
- Max call duration: 180s
- Recording: ON
- Filler/backchannel: ON
- Webhook: `POST https://<our-domain>/webhook/bolna`
- HMAC signing: ON if Bolna supports it; backend verifies via constant-time compare

---

## 6. Backend API surface

All JSON unless noted. Single FastAPI service.

### Orders

```
POST /api/orders/upload                      # multipart CSV
  Response: { inserted: [...], rejected: [{row_number, raw, reason}], total_parsed }

GET  /api/orders?call_status=&bucket=&action_state=&limit=&cursor=
  Response: { orders: [...], next_cursor }

GET  /api/orders/{id}                        # includes last 20 call_events under .events

DELETE /api/orders/{id}                      # demo cleanup; admin-guarded
```

### Call orchestration

```
POST /api/orders/{id}/call
  Response: 202 { call_status: "dialing", bolna_call_id }
  Side: marks order dialing, fires "order.updated"

POST /api/orders/call-batch
  Body: { order_ids: [...] } | { all_pending: true }
  Response: 202 { triggered: [...], failed: [...] }
  Impl: asyncio.gather with semaphore(3) to avoid burst on Bolna
```

### Bolna webhook

```
POST /webhook/bolna
  Headers: X-Bolna-Signature: <hmac>   # if Bolna offers signing
  Server:
    1. Verify HMAC; reject 401 if invalid
    2. Match payload.call_id → order.bolna_call_id
    3. Append raw payload to call_events (type=webhook_received)
    4. Extract transcript + variables → order doc
    5. Run classifier → set bucket
    6. Append call_events (type=bucketed)
    7. Publish "order.updated" → SSE pubsub
  Response: 200 { ok: true }
  Idempotency: if order already has bucket set, no-op + 200 (Bolna may retry)
```

### Seller actions

```
POST /api/orders/{id}/action
  Body: {
    action: "approve_dispatch" | "cancel_dispatch" | "push_new_address"
          | "confirm_reschedule" | "assign_human",
    note: str | null
  }
  Validation: action must be valid for current bucket
    (e.g., push_new_address only when bucket=="address_updated")
  Side: append to actions[], set action_state, append call_events (type=action_taken),
        fan-out "order.updated"
  Response: 200 { order: <updated doc> }
```

### Demo helpers (admin-only, behind `X-Admin-Token`)

```
POST /api/orders/{id}/simulate-outcome
  Body: { bucket: "<one of 5>", reschedule_preference?, updated_address? }
  Effect: writes synthetic transcript + extracted_variables + sets bucket,
          publishes "order.updated". Used to pre-stage rows for demo.

POST /api/orders/reset                       # wipes orders + events for re-takes
```

### Live updates

```
GET /stream                                  # text/event-stream
  Events:
    event: order.updated
    data: { order_id, _id, fields_changed: [...], snapshot: <projection> }

    event: heartbeat
    data: {ts}    # every 15s — keep proxies from idle-closing

  Impl: per-client asyncio.Queue; in-process publish() fans out to all queues;
        async generator yields SSE frames. Caddy flush_interval -1 ensures
        no proxy buffering.
```

### Aux

```
GET /health           # { ok, mongo, version }
GET /api/version
GET /api/stats        # for the impact strip — counts + ROI math
```

### Auth model

- **Bolna webhook:** HMAC verification if available; IP allowlist fallback otherwise.
- **Admin endpoints** (`simulate-outcome`, `reset`, delete): `X-Admin-Token` env-var match.
- **All other endpoints:** unauthenticated — single-tenant demo. Documented as "demo posture"; production drops Cognito or a JWT layer here.
- **CORS:** not required — Caddy serves frontend and proxies backend on the same origin.

### Error model

```
{ error: { code: "ORDER_NOT_FOUND" | "INVALID_CSV_ROW" | "BOLNA_API_FAILED" | ...,
           message: "...", detail: {} | null } }
```

---

## 7. Frontend UI

Single-page React (Vite + TypeScript + Tailwind + shadcn/ui primitives). One main screen, no router.

### Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Snitch • Riya Console                          [Upload CSV] [⚙ Demo ▾]    │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌─ Impact (today) ──────────────────────────────────────────────────┐    │
│ │ Called: 3  •  Confirmed: 1  •  Issues caught early: 2              │    │
│ │ Est. RTO cost saved: ₹260   •   Call spend: ₹24   •   Net: +₹236   │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ [All 3] [Pending 0] [Confirmed 1] [Address 1] [Reschedule 1]              │
│ [Cancel 0] [Escalate 0]                                                    │
│                                                                            │
│ ┌───┬──────────────┬────────────┬──────────────┬───────────────┬────────┐│
│ │ # │ Order        │ Customer   │ Status       │ Outcome       │ Action ││
│ ├───┼──────────────┼────────────┼──────────────┼───────────────┼────────┤│
│ │ 1 │ SNT-051142   │ Ananya S.  │ ✓ Completed  │ ● Confirmed   │ Approve││
│ │ 2 │ SNT-051143   │ Rohit M.   │ ✓ Completed  │ ● Addr Updated│ Push   ││
│ │ 3 │ SNT-051144   │ Priya N.   │ ⟳ Dialing... │ —             │ —      ││
│ └───┴──────────────┴────────────┴──────────────┴───────────────┴────────┘│
│                                                                            │
│  ● live  •  connected via SSE                                              │
└──────────────────────────────────────────────────────────────────────────┘
```

Row click → right-side drawer (60% width on desktop) with order details, outcome, transcript playback link + transcript text, action buttons, event timeline.

### Components

| Component             | Role                                                                 |
|-----------------------|----------------------------------------------------------------------|
| `App.tsx`             | Mounts SSE listener, owns root order store, renders shell + screens  |
| `TopBar`              | Brand label, Upload CSV button, Demo controls dropdown               |
| `ImpactStrip`         | Live-derived counters + ROI math from `/api/stats`                   |
| `BucketTabs`          | Filter chips with counts                                             |
| `OrderTable` + `OrderRow` | Row state-transition animation, primary action button          |
| `OrderDrawer`         | Right-side panel: outcome + transcript + actions + timeline          |
| `UploadModal`         | Dropzone, parse preview, per-row error display                       |
| `DemoControlsMenu`    | Simulate outcome / Trigger all pending / Reset all                   |
| `ConnectionDot`       | Footer indicator: SSE connected / reconnecting                       |

### Bucket → row-action map

| Bucket            | Primary action            | Secondary actions          | Color  |
|-------------------|---------------------------|----------------------------|--------|
| `confirmed`       | **Approve Dispatch**      | Cancel · Assign human       | green  |
| `address_updated` | **Push New Address**      | Approve original · Cancel   | amber  |
| `rescheduled`     | **Confirm New Slot**      | Approve original · Cancel   | indigo |
| `cancel_intent`   | **Cancel Dispatch**       | Override (proceed) · Human  | red    |
| `escalate`        | **Assign to Human**       | Cancel · Approve as-is      | orange |
| `no_answer`       | **Schedule retry**        | Cancel · Assign human       | gray   |
| `failed`          | **Retry call**            | Assign human · Cancel       | gray   |

### Real-time wiring

```ts
const es = new EventSource("/stream");
es.addEventListener("order.updated", (e) => {
  const { snapshot } = JSON.parse(e.data);
  orderStore.upsert(snapshot);   // row animates via key-change
});
es.onerror = () => setConnState("reconnecting");
```

Subtle row animation on bucket change: 800ms color flash via Tailwind transition + a one-shot CSS class.

### Impact strip formula (server-computed, `GET /api/stats`)

```
called           = count(orders where call_status == "completed")
confirmed_count  = count(orders where bucket == "confirmed")
issues_caught    = count(orders where bucket in [address_updated, rescheduled, cancel_intent])

# ROI math — conservative; assumption cited in deck:
#   failed delivery cost = ₹100 (midpoint of ₹80-150)
#   call cost            = ₹8
#   estimated RTOs saved = 1.0 * cancel_intent + 0.6 * address_updated + 0.4 * rescheduled
saved_rto_count  = cancel_intent_count + 0.6*address_updated_count + 0.4*rescheduled_count
cost_saved       = round(saved_rto_count * 100)
call_spend       = called * 8
net              = cost_saved - call_spend
```

### State management

Zustand store, single slice:
```ts
{
  orders: Map<string, Order>,
  connState: "connected" | "reconnecting" | "disconnected",
  filter: { bucket?, call_status? },
  upsert(order), remove(id), setConn(s), setFilter(f)
}
```

### Explicitly NOT building

No login / multi-tenant; no charts library (impact strip is pure text); no table virtualization (≤20 rows in any demo path); no dark mode; no mobile responsive.

---

## 8. Deployment

### Instance

- EC2 **t3.small** (2 vCPU / 2 GB), ap-south-1 (Mumbai)
- Elastic IP (stable Bolna webhook URL across reboots)
- Security group: 80/443 from 0.0.0.0/0, 22 from your IP only
- Ubuntu 24.04 LTS; Docker + Docker Compose installed

### Compose stack

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - ./frontend/dist:/srv          # built React bundle
    depends_on: [api]
  api:
    build: ./backend
    environment:
      - MONGODB_URI
      - BOLNA_API_KEY
      - BOLNA_AGENT_ID
      - BOLNA_WEBHOOK_SECRET
      - ADMIN_TOKEN
      - PUBLIC_BASE_URL
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
volumes:
  caddy_data:
```

### Caddyfile

```
{$DOMAIN} {
    encode gzip
    handle /api/* { reverse_proxy api:8000 }
    handle /webhook/* { reverse_proxy api:8000 }
    handle /stream {
        reverse_proxy api:8000 {
            flush_interval -1
            transport http { read_timeout 0 }
        }
    }
    handle { root * /srv ; file_server }
}
```

### Secrets

`.env` on the box (gitignored), loaded by Docker Compose. Not Parameter Store / Secrets Manager — beyond demo scope. README documents required env vars.

### Deploy command

`docker compose up -d --build`. Update loop: ssh → `git pull` → repeat. Small `deploy.sh` for convenience.

### MongoDB Atlas

M0 free cluster in ap-south-1. Network access: EC2 elastic IP only. Database `riya`, two collections.

---

## 9. Demo orchestration

### Pre-recording prep (night before)

1. Seed `demo_orders.csv` with **3 rows**:
   - **Row 1:** your real phone, Snitch COD ₹1,499, slot "kal subah 10-1 baje".
   - **Row 2:** spare/test number, Snitch prepaid, slot "kal shaam 4-7 baje".
   - **Row 3:** spare/test number, Snitch COD ₹2,299, slot "parso subah".
2. Dry-run a real Bolna call on Row 1 — verify end-to-end and capture a known-good recording as a Plan B fallback.
3. Decide pre-staged outcomes via `POST /simulate-outcome`:
   - Row 2 → `address_updated` with believable new-address verbatim.
   - Row 3 → `cancel_intent` (highest-ROI bucket, anchors the ROI narrative).
4. `POST /api/orders/reset` so the dashboard starts clean on recording day.

### Recording script (5-7 min)

| Min  | Beat |
|------|------|
| 0:00 | Open `https://<your-domain>` — empty dashboard, impact strip at zeros |
| 0:30 | Click **Upload CSV** → drag `demo_orders.csv` → 3 rows appear as `pending` |
| 1:00 | Narrate use case (RTO, 4-step check, brand context) — 60s |
| 2:00 | Click **Trigger calls** → Row 1 phone rings on camera, you answer |
| 2:10 | Live conversation with Riya in Hinglish — identity → address → available → COD → confirmed |
| 4:00 | Call ends → Row 1 animates to `confirmed`, impact strip ticks up |
| 4:15 | Open **Demo controls** → simulate Row 2 outcome → animates to `address_updated` |
| 4:30 | Click Row 2 → drawer → show transcript + new address → **Push New Address** → action_state updates |
| 5:00 | Simulate Row 3 outcome → `cancel_intent` → drawer → **Cancel Dispatch** → narrate ROI |
| 5:45 | Impact strip recap: "₹260 saved on 3 calls costing ₹24 — 11× ROI today; at 5k daily orders, ₹2-4 cr/yr saved" |
| 6:30 | Close on architecture overview slide |

### Fallback plans

- **Plan A:** re-dial if the live call fails (Bolna calls are cheap).
- **Plan B:** simulate Row 1 outcome with the pre-captured dry-run transcript, narrate as "here's a previous run".
- **Plan C:** cut to a separately-recorded call clip overlaid on screen.

---

## 10. Error handling

| Failure                                  | Behavior                                                                                                  |
|------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| CSV row invalid (bad phone, missing col) | Reject row, surface in upload-modal banner with row_number + reason. Other rows still ingest.            |
| Bolna API rejects call-create            | Mark order `call_status="failed"`, log payload in `call_events`, row shows "Retry call" action.          |
| Webhook for unknown call_id              | Log to `call_events` (type=error), return 200, alert in server logs (don't make Bolna retry forever).    |
| Webhook HMAC fails                       | Return 401, log to `call_events`, do not mutate order.                                                   |
| Webhook arrives twice (idempotency)      | If order has `bucket` set, no-op + 200. Log duplicate event.                                              |
| Mongo unreachable                        | API returns 503 with retry-after; Caddy returns 502 to client; footer shows disconnected.                |
| SSE proxy drops                          | EventSource auto-reconnects; on reconnect, re-sync via one-shot `GET /api/orders`.                       |
| Webhook never arrives (call hung)        | Background sweeper task: every 60s, orders `dialing` for >5 min → `call_status="failed"`, log timeout.   |
| Customer hangs up mid-call               | Bolna sends partial transcript + `needs_human=true` → bucket `escalate`.                                  |

---

## 11. Testing

### What we test

- **CSV parser** — pytest unit tests: happy path, malformed rows, phone normalization, unknown columns, BOM.
- **Bucket classifier** — pure-function pytest, table-driven across all variable combinations.
- **Webhook signature verification** — HMAC happy path + replay/tamper rejection.
- **One end-to-end test** — pytest + httpx: upload CSV → simulate webhook payload → assert order doc has correct bucket + transcript. Mongo via `mongomock-motor` or ephemeral docker service.
- **CI:** GitHub Actions free tier — lint (ruff) + pytest on every push. <60s wall time.

### What we skip

Frontend unit tests (manual QA on the dry-run is enough). Load testing (3-order demo). Integration tests against real Bolna API (one dry-run call is the contract test).

---

## 12. Risk register

| Risk                                                            | Likelihood | Mitigation                                                                                                                 |
|-----------------------------------------------------------------|-----------|---------------------------------------------------------------------------------------------------------------------------|
| Bolna webhook payload shape differs from spec assumptions       | High      | Defensive parser — accept raw, log, extract known fields. Run a real call early to lock the contract before building UI. |
| Live call fails on recording day (network/telco/Bolna)          | Medium    | Pre-captured Plan B + cut-in Plan C.                                                                                       |
| MongoDB Atlas IP allowlist blocks EC2 after instance change     | Medium    | Use Elastic IP from day one; Atlas allowlist scoped to it; verify pre-recording.                                          |
| Caddy SSE buffering trips                                       | Low       | Fall back to 5s long-polling — small code change, no demo impact.                                                          |
| Hinglish voice quality unconvincing                             | Medium    | A/B test Bolna voices early; tune filler/pauses; keep call short.                                                          |
| Demo presenter (you) freezes mid-call                           | Low       | Rehearse the Riya call 3-5 times; have a script card off-camera.                                                           |
| Atlas free tier rate-limits                                     | Very low  | Demo load is trivial.                                                                                                       |

---

## 13. Out of scope (deliberately)

- Multi-tenant brand switching / login / RBAC.
- Real 3PL APIs (Shiprocket/Delhivery/Ecom Express) — action buttons are stubs that record state changes only.
- Control-cohort RTO analytics with real before/after numbers (impact strip is forward-looking estimate from bucket distribution + assumptions).
- Mobile-responsive layout.
- Charts / dashboards beyond the impact strip.
- Worker pool / queue / retry orchestration (Celery, Redis).
- Production secrets management (Parameter Store / Secrets Manager).
- Horizontal scaling of FastAPI (single-worker SSE constraint).
- Customer self-serve web portal (SMS-link rescheduling fallback channel).
- Languages beyond Hinglish + English.

---

## 14. Open questions to verify during build

1. **Bolna's exact create-call request shape** — variable-substitution syntax, agent_id format, response payload. Verify against current Bolna API docs before coding the dispatch helper.
2. **Bolna's exact webhook payload shape** — transcript format (turn-by-turn vs flat string), where `extracted_variables` lives, presence/absence of HMAC headers. Verify from the dry-run.
3. **Bolna's no-answer / failure call_status values** — exact enum strings. Verify from a deliberately-missed dry-run call.
4. **Recording URL availability + access** — does Bolna serve the recording publicly (signed URL) or do we need to download + re-host? Verify from dry-run.
5. **Hinglish voice options** — pick the most natural-sounding female voice for the Indian context from Bolna's available voices.

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

## Brand styling

- Primary: white (`#ffffff`)
- Secondary: `#11b993`
- Font: Geist Sans

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

Run backend tests:
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

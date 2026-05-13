# Doorbell — AWS deploy runbook

Target architecture: single EC2 (ap-south-1) running Docker Compose with Caddy
serving two subdomains of `chatroute.in`.

- **`doorbell.chatroute.in`** → React build (static)
- **`api.chatroute.in`** → FastAPI (REST + Bolna webhook + SSE)

Caddy handles TLS for both via Let's Encrypt. MongoDB Atlas stays remote.

---

## 0. Inventory before you start

You'll need:

- AWS account with IAM permissions to launch EC2 + manage security groups in `ap-south-1`
- Hostinger DNS panel access for `chatroute.in`
- MongoDB Atlas account (the one already configured — you'll add an IP to its allowlist)
- Bolna dashboard access (you'll update one webhook URL)
- An SSH keypair for the EC2 instance

## 1. Launch the EC2 instance

In the AWS console:

1. EC2 → **Launch instance** in **ap-south-1 (Mumbai)**
2. **Name**: `doorbell`
3. **AMI**: Ubuntu Server 24.04 LTS (x86_64)
4. **Instance type**: `t3.small` (2 vCPU, 2 GB) — comfortable; `t3.micro` works but tight under build
5. **Key pair**: select or create one; save the `.pem` locally
6. **Network settings → Edit**:
   - **Security group** — Create new with three rules:
     | Type | Port | Source | Notes |
     |---|---|---|---|
     | SSH | 22 | My IP | locked down |
     | HTTP | 80 | 0.0.0.0/0 | Let's Encrypt validation |
     | HTTPS | 443 | 0.0.0.0/0 | normal traffic |
7. **Storage**: 16 GiB gp3 is plenty
8. **Launch**

## 2. Allocate an Elastic IP

EC2 → **Elastic IPs** → **Allocate** (ap-south-1) → select the new IP → **Associate** → pick your `doorbell` instance.

Note this IP. You'll use it in three places:
- Hostinger DNS records
- MongoDB Atlas allowlist
- This document's commands below

## 3. DNS records at Hostinger

Hostinger → **Domains** → `chatroute.in` → **DNS / Name servers** → **Manage**.

Add two A records:

| Type | Name | Points to | TTL |
|---|---|---|---|
| A | `api` | `<elastic-ip>` | 14400 |
| A | `doorbell` | `<elastic-ip>` | 14400 |

Save. DNS propagation usually 1–5 min for Hostinger.

Verify from your laptop (replace IP):
```bash
dig +short api.chatroute.in
dig +short doorbell.chatroute.in
# Both should return your elastic IP.
```

## 4. MongoDB Atlas allowlist

Atlas → your cluster → **Network Access** → **Add IP Address** → enter your elastic IP → **Confirm**.

(While there, double-check the SRV connection string in your Atlas cluster's
"Connect" panel — you'll paste it into the EC2 `.env` shortly.)

## 5. SSH into the instance + bootstrap

```bash
ssh -i /path/to/your-key.pem ubuntu@<elastic-ip>
```

Once on the box:

```bash
# Install Docker + Compose plugin
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
newgrp docker

# Clone the repo
git clone <your-repo-url> doorbell
cd doorbell

# Copy and fill .env
cp .env.example .env
nano .env
```

In `.env`, set:
```
DOMAIN_WEB=doorbell.chatroute.in
DOMAIN_API=api.chatroute.in
PUBLIC_BASE_URL=https://api.chatroute.in
CORS_ORIGINS=https://doorbell.chatroute.in

MONGODB_URI=mongodb+srv://USER:PASS@your-cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=riya

BOLNA_API_KEY=<your real key>
BOLNA_AGENT_ID=<your Riya agent id>
BOLNA_WEBHOOK_SECRET=
BOLNA_BASE_URL=https://api.bolna.ai

ADMIN_TOKEN=<random 32+ char string — generate with: openssl rand -hex 24>
```

## 6. First deploy

Still on the EC2 box, repo root:

```bash
./deploy.sh
```

This will:
1. `git pull --ff-only` (no-op on first run)
2. Build the React bundle inside a node:22-alpine container with
   `VITE_API_BASE_URL=https://api.chatroute.in` baked in
3. `docker compose up -d --build` — starts Caddy + api containers
4. Curl `https://api.chatroute.in/health` to verify

First boot, Caddy will request Let's Encrypt certs for both subdomains. It
needs port 80 reachable (security group) and DNS pointing correctly. Logs in
`docker compose logs caddy` will show:

```
certificate obtained successfully ... doorbell.chatroute.in
certificate obtained successfully ... api.chatroute.in
```

## 7. Update Bolna's webhook URL

In the Bolna dashboard → Agent Setup → your Riya agent → **Analytics** tab →
"Push all execution data to webhook":

Change from your old ngrok URL to:
```
https://api.chatroute.in/webhook/bolna
```

Click **Save agent** (top right).

You can now stop the local ngrok tunnel — Bolna will send webhooks directly
to your EC2 host.

## 8. Smoke test the full loop

From your laptop:

```bash
# 1. API reachable?
curl https://api.chatroute.in/health
# {"ok":true,"service":"riya-backend","mongo":true}

# 2. Dashboard loads?
open https://doorbell.chatroute.in

# 3. SSE stream open (will hang — that's correct; Ctrl-C after a few seconds)
curl -N https://api.chatroute.in/stream

# 4. End-to-end: upload demo CSV, trigger one real call from the dashboard,
#    answer your phone, watch the row flip to its bucket.
```

## 9. Day-2 operations

**Redeploy after a code change:**
```bash
ssh ubuntu@<elastic-ip>
cd doorbell
./deploy.sh
```

**Watch logs:**
```bash
docker compose logs -f api      # backend
docker compose logs -f caddy    # web + TLS
```

**Restart just the API (e.g. after `.env` change):**
```bash
docker compose restart api
```

**Free disk if needed:**
```bash
docker system prune -af --volumes
```

**Mongo: query straight from the box:**
```bash
docker run --rm -it --network host mongo:latest \
  mongosh "$MONGODB_URI"
```

## 10. Things that can bite you

| Symptom | Cause | Fix |
|---|---|---|
| `curl https://api.chatroute.in/health` returns SSL error / no route | DNS not propagated, or Caddy hasn't issued cert yet | wait 2-3 min after first deploy; `docker compose logs caddy` will show cert progress |
| API logs say `ServerSelectionTimeoutError` on Mongo | Atlas IP allowlist doesn't include elastic IP | Atlas → Network Access → add it |
| Dashboard loads but no orders appear | CORS — frontend can't reach API | check `CORS_ORIGINS=https://doorbell.chatroute.in` (exact, no trailing slash); restart api |
| Browser console shows EventSource `net::ERR_FAILED` on `/stream` | CORS or Caddy SSE buffering | confirm CORS as above; Caddyfile must have `flush_interval -1` (already set) |
| Bolna calls fire but no webhook lands | Bolna's agent still points at old ngrok URL | update webhook URL in Bolna dashboard (§7) |
| Phone never rings on a triggered call | Bolna trial plan + unverified number | verify the recipient number in Bolna → My Numbers |
| Calls 502 from `/api/orders/{id}/call` | Wrong `BOLNA_BASE_URL` or stale `BOLNA_AGENT_ID` | check `.env` matches the Bolna dashboard; restart api |

## 11. (Optional) Lock down further before sharing the link

- **Cloudflare in front** of both subdomains — proxied (orange cloud) gets you DDoS protection, caching, and hides your origin IP. Set Cloudflare to "Full (strict)" so it validates Caddy's Let's Encrypt cert end-to-end.
- **Basic auth on the dashboard** — Caddy can add it in two lines if you want to keep the demo private:
  ```
  {$DOMAIN_WEB} {
      basicauth { reviewer JDJhJDE0... }   # bcrypt hash
      ...
  }
  ```
  Hash with: `caddy hash-password`
- **Drop SSH from public** — once you're set up, move SSH to a session-manager
  shell or a bastion. Day-2 cost = low; security upside = high.

---

That's it. The whole runbook should take 30-40 minutes end-to-end if DNS
propagation cooperates.

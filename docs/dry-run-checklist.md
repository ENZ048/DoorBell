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

- [ ] Edit `scripts/demo_orders.csv` Row 1 to use your real Indian mobile number
- [ ] In the dashboard, click **⚙ Demo ▾** → enter `ADMIN_TOKEN`
- [ ] Click **Reset all** so the dashboard is clean
- [ ] Click **Upload CSV** → upload `scripts/demo_orders.csv`
- [ ] Confirm 3 rows appear as `pending`
- [ ] Click **Trigger call** on Row 1; your phone should ring within 10s
- [ ] Run the full 4-step conversation: identity → address ("yes") →
  availability ("yes") → COD intent ("haan, ready hai")
- [ ] After hang-up, Row 1 should flip to `confirmed` within ~30s
- [ ] Open Row 1 drawer; confirm transcript and recording link are present

## 4. Capture a Plan B fallback

- [ ] Screen-capture Row 1's transcript and recording so we have a Plan B
  if the live call fails on recording day
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

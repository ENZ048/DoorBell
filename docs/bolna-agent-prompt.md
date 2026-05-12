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

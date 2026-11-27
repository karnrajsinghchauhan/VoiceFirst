# Launch costs: a live call-in demo

What it takes to turn /demo into a real Indian number anyone can ring, answered by the agent in Hinglish. **Nothing here has been bought or signed up for.** Each line waits for Karn's "yes" in chat (NEXT.md section 4). Prices were checked on 2026-11-27; re-check before paying. "Estimate" means we could not find a published price.

## Two things to know first
1. **The engine places calls; it does not answer them yet.** Inbound (J4) is an interface stub. A number people can ring needs an inbound path: a LiveKit SIP inbound trunk and dispatch rule, and a small inbound agent entry that runs the same guardrails with a demo booking. Estimate: 3-5 days of build. The no-build alternative is a "call me" form, where the visitor enters their own number on the private /demo and the engine calls them on the existing outbound path. That counts against the 20-call test cap and needs the same keys.
2. **Indian numbers need an Indian business.** Plivo rents Indian numbers only to Indian-registered businesses after KYC (a certificate of incorporation and a GST certificate, per Plivo's support pages), paid in INR. That depends on the [CD] legal entity and GSTIN.

The real provider clients (Sarvam, OpenAI/Anthropic, LiveKit SIP, Meta WhatsApp) are on branch `v3/w1-providers-crm` (PR #12) and must be merged first.

## Shopping list
Volume assumption for the monthly figures: 300 demo calls of 2 minutes, 600 minutes a month (estimate).

| # | Item | Plan | Monthly cost | Setup time | Documents needed | Env vars |
|---|------|------|--------------|------------|------------------|----------|
| 1 | Sarvam API key (speech to text, Bulbul text to speech) | Pay as you go | STT Rs 0.49/min, TTS Rs 3.00 per 1,000 characters ([pricing](https://docs.sarvam.ai/api-reference-docs/getting-started/pricing)); at 600 min about Rs 300 STT + Rs 760 TTS = **about Rs 1,060** (estimate) | 1 hour | Account, payment method; business details [CD] | `AV_STT=sarvam`, `AV_TTS=sarvam_bulbul`, `SARVAM_API_KEY`, `AV_SARVAM_STT_MODEL`, `AV_SARVAM_TTS_MODEL` |
| 2 | One LLM key | OpenAI (gpt-4.1-mini reported at USD 0.40 in / 1.60 out per million tokens) or Anthropic (Claude Haiku 4.5 reported at USD 1 / 5) | About 2 million tokens a month at demo volume: **under USD 5** (estimate; prices reported by third parties, confirm on the provider page; model availability changes) | 1 hour | Account, card; for production an India-region or zero-retention agreement [CD] | `AV_LLM=openai` + `OPENAI_API_KEY` + `AV_OPENAI_MODEL`, or `AV_LLM=anthropic` + `ANTHROPIC_API_KEY` + `AV_ANTHROPIC_MODEL` |
| 3a | LiveKit Cloud (recommended for the demo) | Build: USD 0, 1,000 agent-session minutes, 5 concurrent sessions; Ship: USD 50 ([pricing](https://livekit.com/pricing)) | **USD 0** at 600 min (Build); USD 50 if the demo outgrows it | 1 hour | Account | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` |
| 3b | LiveKit self-hosted (alternative) | Open source, Apache 2.0 | Runs on the host in item 5; **no licence cost**, more operations work (livekit-server, livekit-sip, Redis, TURN) | 1-2 days | None | Same three `LIVEKIT_*` vars pointing at your server |
| 4a | Plivo India number and minutes (recommended) | Pay as you go | Number **Rs 200/month**; calls **Rs 0.38/min** in and out, 30-second pulse ([India pricing](https://www.plivo.com/voice/pricing/in/)); at 600 min about Rs 230. Total **about Rs 430** | KYC about 1 hour to 1 business day after documents | Indian-registered business: certificate of incorporation, GST certificate (confirm in the Plivo console under KYC); Indian payment card | `AV_TELEPHONY=plivo`, `AV_SIP_OUTBOUND_TRUNK_ID` (outbound); an inbound trunk and dispatch rule in LiveKit (inbound, not built) |
| 4b | Exotel (alternative) | Quote only for SIP; plans from about Rs 9,999 for 5 months reported by third parties | **Estimate only**; ask Exotel sales in writing | Days (sales-led) | Indian business KYC | `AV_TELEPHONY=exotel`, `AV_SIP_OUTBOUND_TRUNK_ID` |
| 5 | Backend host in India (engine + Postgres) | DigitalOcean BLR1: a 2 vCPU / 4 GB Droplet and managed PostgreSQL | Droplet **about USD 24** (estimate; DigitalOcean prices one list across regions); managed PostgreSQL **from USD 15** ([pricing](https://www.digitalocean.com/pricing/managed-databases)). Total **about USD 39** | Half a day | Account, card | `AV_ENVIRONMENT=production`, `AV_DATABASE_URL` (non-superuser role), `AV_DATA_KEY`, `AV_PHONE_PEPPER`, `AV_DEMO_PASSCODE`, `AV_TENANT_ID` |
| 6 | Vercel Pro (web app) | Pro | **USD 20 per member seat** ([plan docs](https://vercel.com/docs/plans/pro-plan)); Hobby is for non-commercial use only | 15 minutes | Account, card | `AV_API_MODE=http`, `AV_API_URL`, `AV_DEMO_PASSCODE`, `NEXT_PUBLIC_BRAND_NAME`, `NEXT_PUBLIC_LEGAL_ENTITY_NAME`, `NEXT_PUBLIC_LEGAL_GSTIN`, `NEXT_PUBLIC_LEGAL_ADDRESS`, `NEXT_PUBLIC_CONTACT_EMAIL`, `NEXT_PUBLIC_SITE_URL` |

## Total, recommended path (items 1, 2, 3a, 4a, 5, 6)
About Rs 1,490 + USD 64 a month, roughly **Rs 6,900 a month** at an assumed USD 1 = Rs 84 (estimate), plus GST where it applies. One-off: no setup fees found for the recommended path.

## Not needed for the demo
- WhatsApp Business verification and Meta Cloud API (the demo can show the template without sending it). Needed for the pilot: Meta business verification, an approved utility template, and `AV_WHATSAPP=meta_cloud_api` + `AV_META_ACCESS_TOKEN`.
- A domain: `ownermeetings.com` is the configured site URL (D-701), but its ownership is [CD]. Vercel's free `*.vercel.app` works for a passcode-gated demo.
- Kafka: the demo uses the in-memory bus.

## Order of work after Karn's yes
1. Merge PR #12 (provider clients) after its own checks.
2. Legal entity and GSTIN, then Plivo KYC (the longest wait).
3. Sarvam and LLM keys into the host's secret store; run `make eval-audio` on real speech (no calls).
4. LiveKit project, SIP trunk to the Plivo number; the 20 approved test calls to Karn's own phones only, counted in STATUS.md.
5. Build the inbound entry (3-5 days) or ship the "call me" form first.

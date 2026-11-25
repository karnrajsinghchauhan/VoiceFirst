# Agoda Voice: product, platform and launch brief (v3)

Owner: Karn, founder. Continues the engine built under brief v2 (engineering rules, the five promises, the REQ table, the tester and the [V]/[CD] tags all still apply). Goal: turn the engine into a done-for-you enterprise platform that looks and behaves like a serious company's product, where every claim is true.

## 0. How to run
- **0.1** Pre-approved. Post a plan of 15 lines or fewer, then build. Stop only for: (a) money or paid signups; (b) irreversible actions outside the repo; (c) genuine contradictions. Log every decision in DECISIONS.md.
- **0.2 Spending gate.** These need Karn's explicit "yes" in chat before anything is created or billed:
  - Vercel Pro (the Hobby plan is non-commercial);
  - backend hosting;
  - LiveKit Cloud;
  - Sarvam, LLM, ElevenLabs, Plivo or Exotel keys;
  - domains and phone numbers;
  - WhatsApp Business verification.

  Until then: prepare configs, IaC and docs, run locally, and list each item with its monthly cost in docs/launch-costs.md.
- **0.3** Never place real calls or send real WhatsApp messages, except the 20 approved test calls with keys Karn puts in .env.
- **0.4** Survival: push to GitHub (karnrajsinghchauhan/VoiceFirst) after every milestone, with one PR per milestone.
- **0.5 Truth rule** (enforced by web/tests/claims.test.ts):
  - every number on a public page comes from docs/sources.md (dated) or a measured result in reports/ (dated, with method), or is labelled "estimate";
  - no superlatives without a measured comparison;
  - no logos, testimonials, certifications or partnerships that don't exist;
  - the test fails on banned phrases and on numbers without a source anchor.

## 1. What the product is
- **For Agoda:** an AI calling service in Hindi, English and Hinglish that recovers failed payments and confirms bookings for India customers. It complies with TRAI's 2026 AI-call rules, is measured against a no-call holdout, and always hands money decisions to a human.
- **For us:** a done-for-you platform. ProsperOps sets it up, runs it, improves it weekly, and can hand it over onto the client's own Kubernetes.
- Keep it simple: one console, one public site, one docs site, one AI concierge, one engine.

## 2. How the enterprise voice platforms present themselves (match the substance, not the look)
Vapi, Retell, ElevenLabs Agents, PolyAI and Sierra all show buyers the same things. Build our honest version of each:
- a live "talk to it" agent;
- real docs: quickstart, architecture, API reference, SDK snippets, webhooks, changelog;
- a trust centre: controls, data flow, sub-processors, retention, DPA, compliance status ("planned" where true), disclosure address;
- a status page with uptime history;
- transparent pricing with an enterprise path;
- enterprise features: SSO, RBAC, audit logs, concurrency limits, residency, SLAs, support;
- buyer observability: call logs, transcripts, QA scores, cost per call, latency.

Copy no vendor's design, copy, illustrations or code.

## 3. Build, in order
- **S1 Identity-first openings.** DONE on main.
- **S2 Commit safety.** DONE on main.
- **S3 Real providers (behind the spending gate).**
  - Clients: Plivo or Exotel SIP via LiveKit SIP; Meta WhatsApp Cloud API; the LiveKit media bridge (M8).
  - Each is fully implemented, contract-tested against recorded fixtures, and switched on only by config plus real keys.
  - DONE = green with mock config. After Karn's yes: audio evals on 2 line profiles, p50 under 800 ms, p95 under 1,500 ms, calls counted against the cap of 20.
- **S4 Feedback loop.**
  - Per-call QA scorecard: disclosure, identity, guardrails, outcome, tone, latency, cost.
  - Nightly clustering of failed and low-score calls by cause: misheard amount, missed opt-out, slow tool, wrong language, confusion.
  - A weekly docs/weekly-review/<date>.md with the top 5 causes, example redacted call ids and a proposed fix for each. Each fix is a PR; prompt fixes include a reproducing persona.
  - Nothing deploys without the eval gate and a named human approving the PR. The system never edits its own production prompts.
  - A drift alert fires if containment, CSAT, complaint rate or p95 latency moves more than a configured threshold week on week.
  - DONE = a seeded synthetic week produces a review with clustered causes and 3 draft fix PRs, each with a reproducing persona.
- **S5 CRM loop.**
  - Field mapping in crm/mappings/<crm>.yaml; adapters for Zendesk, Salesforce and HubSpot, plus mock.
  - For every handled call, write: ticket or activity with the outcome, masked booking ref, 5-line handoff summary, QA score, an access-controlled redacted transcript link, cost, next action and owner.
  - Idempotent upserts keyed by call_id. Failures go to a dead-letter queue with an alert; no silent drops.
  - Outbound webhooks: HMAC-signed, timestamped, replay-protected.
  - DONE = e2e writes to a mock Zendesk for 100% of handled calls; a replayed webhook is rejected; a forced CRM outage lands in the DLQ and alerts.
- **S6 Telephony, numbers and costs.**
  - Console "Numbers" page: each CLI with series (140, 1600, 1601), purpose, operator, A2P declaration ref and date, status, complaints in the rolling 10 days, answer rate, auto-pause.
  - docs/telephony.md and /docs/telephony, in plain words: few declared numbers per telecom circle, not rotation (undeclared AI calls count as spam under TRAI 2026, and rotation looks like spam); 140 for promotional, 1600/1601 for service; verified caller ID (Truecaller, CNAP [CD]); a WhatsApp heads-up before the call and a follow-up after a missed one; a "Call me now" button; caps and cooldowns.
  - docs/unit-economics.md and a console "Costs" page: cost per minute and per resolved contact, one line per component (telephony, A2P termination, STT, LLM, TTS, orchestration and infra, WhatsApp, storage and QA). Every price comes from config with source URL and checked date; defaults are marked "re-check before quoting".
  - A comparison with the published Vapi, Retell and ElevenLabs list prices, nothing beyond them.
  - DONE = changing a unit price updates every cost view and the proposal's cost table; the claims test passes.
- **S7 Enterprise features.**
  - Done on main: SSO (OIDC, SAML-ready), RBAC, audit export, tenant isolation by Postgres RLS with a failing cross-tenant test, scoped hashed rotatable API keys, residency validator.
  - Left: concurrency limits per tenant and per number; rate limits on the public API; envelope encryption (per-tenant data key wrapped by a KMS-style master key, local-file KMS for dev, production KMS [CD]); retention per purpose with a nightly purge and a purge report.
- **S8 Security and operations (OWASP ASVS L2 as the checklist).**
  - Documents: STRIDE threat model (site, console, API, telephony, WhatsApp webhooks, CRM sync, LLM including caller prompt injection); a CycloneDX SBOM per release; SECURITY.md; docs/incident-response.md (CERT-In 6 h, DPDP 72 h); docs/backup-restore.md; an honest one-page SIG Lite/CAIQ-style answer sheet.
  - CI gates, failing on findings above Low: pip-audit, npm audit, gitleaks, semgrep, trivy. Images signed with cosign and built reproducibly.
  - Web: strict CSP, HSTS, XFO, Referrer-Policy; Secure/HttpOnly/SameSite cookies; CSRF on the console; rate limiting and bot protection on public forms and the concierge.
  - Every inbound webhook signature-verified with replay protection.
  - Ops: a timed backup/restore drill recorded in reports/; a status page fed by real health checks; /.well-known/security.txt.
  - DONE = all gates green, restore drill passes, every threat-model mitigation has a test or control reference.
- **S9 AI concierge.**
  - Public site text chat; voice after keys are approved.
  - Retrieval over /docs, the trust centre and pricing only, always citing the page used. Says when unsure and offers a call. Never invents customers, certifications or prices.
  - Books meetings (calendar adapter: mock now, Cal.com later) and captures a lead to the CRM with recorded consent.
  - Guardrails: injection tests, topic boundary, PII minimisation.
  - Evals: 50 questions with expected sources plus 20 adversarial. DONE = at least 95% correct with citations, 100% on adversarial.
- **S10 Live demo (/demo, private, noindex, passcode in env).**
  - Left: a phone panel with scenarios (failed UPI payment, confirmation call, angry refund, "stop calling me", child answers, card number read out) and a Call button. Text mode works without keys.
  - Right: a live timeline of holdout check, each gate pass/fail, clearance, disclosure, tool calls, WhatsApp preview, CRM ticket, QA score, cost, per-turn latency.
  - A kill switch that visibly stops a running campaign in under 5 s. Uses the real engine through /simulate.
  - DONE = a Playwright test runs every scenario; docs/demo-script.md gives Karn a 5-minute talk track.
- **S11 Deploy (behind the spending gate).**
  - Web on Vercel: preview per PR, production on Karn's domain.
  - Engine (FastAPI and the LiveKit worker are long-running, so not Vercel functions) on one container host in an India or Singapore region; record the choice in DECISIONS.md.
  - Managed Postgres in the same region; a Kafka-API service only if the demo needs it.
  - IaC, docs/configuration.md, secrets only in the platform store.
  - DONE = a dry-run deploy plan with exact monthly costs in docs/launch-costs.md, waiting for Karn's yes.

## 4. docs/setup-runbook.md for Karn
For each step: the account, exact setting, cost, approval time and documents needed (GSTIN, incorporation certificate, PAN, address proof).
1. Company and KYC basics.
2. An LLM key, with region and data-retention settings.
3. Sarvam STT/TTS plans and rates.
4. LiveKit Cloud vs self-hosted, the trade-off in 3 lines.
5. Telephony: Plivo or Exotel India KYC; DLT Principal Entity registration (the client as PE, us as telemarketer, or under the client's PE [CD]); A2P CLI declaration; number series per purpose; SIP trunk to LiveKit SIP.
6. WhatsApp: Meta Business verification, display name, utility templates (payment link, confirmation, missed-call follow-up) with exact text in Hindi, Hinglish and English, opt-in capture.
7. Truecaller Business and CNAP [CD].
8. CRM sandboxes: Zendesk trial, HubSpot free, Salesforce developer org.
9. Where each key goes (env name), how it is rotated, who can see it.
10. A test plan for the 20 real calls: Karn's own phones only, which scenarios, what is measured.

## 5. Missing-steps review (after S11)
Three reviews by subagents that have not seen the code being written, given only the repo, docs and this brief. Each writes reviews/<role>.md ranked by severity.
- **R1, Agoda's CX director:** resolution time, humans in charge, tool fit, what would stop a purchase.
- **R2, security and privacy:** ASVS L2, DPDP and CERT-In gaps by severity.
- **R3, staff engineer at a top voice-AI company:** latency, turn-taking, failure modes, observability, 200 concurrent calls, Kubernetes transfer.

Fix every High and Critical with the smallest change, re-run tests, list the Mediums in PLAN.md.

## 6. Front end: a real company, not an AI template
- **Type:** one UI sans (Inter or Geist) plus one display face; tight scale, generous line height; Devanagari in Noto Sans Devanagari or Mukta.
- **Palette:** near-black and off-white, one accent, status green and red only for meaning. No purple-to-blue gradients, glowing orbs, glassmorphism, emoji, stock AI art or 3D blobs.
- **Real product:** the hero is the actual demo timeline (S10); screenshots come from the real console with seeded data.
- **Copy:** short, concrete, sourced, Indian specifics (UPI, TRAI, Hinglish). Banned: "revolutionise", "unlock", "seamless", "cutting-edge", "in today's fast-paced world". Write web/copy/style.md; claims.test.ts enforces the list.
- **Layout and motion:** 8-pt spacing, 12-column grid, consistent max widths, one idea per section; 150–250 ms transitions, no parallax, prefers-reduced-motion respected.
- **Craft:** Lighthouse 95+ on all four scores, no layout shift, self-hosted fonts with swap, AVIF/WebP, WCAG 2.2 AA.
- **Footer:** legal entity, GSTIN, registered address, domain email, and links to terms, privacy, DPA, sub-processors, security.txt and status.
- **Pages:** / (hero with live timeline, problem, how a call works, five promises, dated proof, private deployment, pricing logic, FAQ, concierge, book a call), /product, /security, /pricing, /docs, /changelog, /status, /company, /legal/* (terms, privacy, DPA template, sub-processors, AUP), /agoda (private, noindex, passcode), /demo (private).
- **Disclaimer** on every public page: "{BRAND_NAME} is an independent product by {LEGAL_ENTITY_NAME}. Not affiliated with or endorsed by Agoda." No Agoda logo, font or colours.
- **Brand:** "Agoda Voice" appears only on private pitch pages. The public name is BRAND_NAME [CD, Karn chooses]. Domain ownermeetings.com; flag in DECISIONS.md that it may deserve its own subdomain or brand.

## 7. /agoda: long-form letter to Agoda's CX leadership (2,500–4,000 words, diagrams, print-to-PDF)
Every [V] fact links to docs/sources.md; [CD] items appear only as questions.
1. What we built, in one paragraph.
2. What Agoda already does well: humans in charge, AI voice with suppliers, falling cost per booking. Why voice for India customers is the next layer.
3. India specifics: Hinglish (MakeMyTrip, 70% of voice queries [V]); TRAI's 18 Sep 2026 A2P rule; the DPDP timeline.
4. How one call works: a diagram and a real demo transcript.
5. The five promises: how each is enforced and tested.
6. Proof, dated with method, labelled "measured on test data": tests, the compliance proof, evals, latency.
7. Numbers and telephony: declared numbers, verified caller ID, the WhatsApp loop.
8. Your systems: Kafka, Zendesk, CCaaS handoff, Kubernetes transfer, with honest integration effort in days.
9. Security and data: a trust-centre summary.
10. The pilot: 8 weeks, India-originating bookings, payment rescue plus confirmation, a 10% holdout, success metrics, $20k fixed with half at risk. After that: retainer plus per-resolved-contact pricing, build-operate-transfer.
11. What we need from you: the discovery questions.
12. Who we are: founder, company details, contact. Honest.

## 8. Final deliverable
A phone-friendly summary:
- what's live locally vs deployed, with links;
- eval, concierge, security-gate and restore-drill results;
- the spending list waiting for Karn's yes (item, monthly cost, why);
- top 5 risks and next 5 tasks;
- real calls used (of 20);
- the open [CD] list.

Push and notify.

# Plan

Milestones from the build brief section 14. Status is tracked in STATUS.md.

| M | Scope | Owner workstream |
|---|-------|------------------|
| M0 | PLAN, DECISIONS (D-001..), discovery questions, sources | lead |
| M1 | JSON Schemas, generated pydantic + TS types, drift check, `make up` | lead |
| M2 | All REQ-* tests, state-machine proof (10k), unforgeable GateClearance | W-A |
| M3 | Text-mode agent, tools, guardrails, normaliser, `make demo`, 30 personas | W-B, W-C |
| M4 | 1,000 seeded bookings: ~100 held out, 0 holdout dials, caps honoured | W-D |
| M5 | Post-call, CRM (mock + Zendesk), handoff summaries, kill switch < 5 s | W-E |
| M6 | Lift vs holdout (95% CI), recovery, resolution time, CSAT, cost/contact | W-D |
| M7 | Console with RBAC, Playwright | W-F |
| M8 | Real voice over WebRTC (blocked: no keys) | W-B |
| M9 | Marketing site + docs | W-F |
| M10 | Helm, sizing, licence table | lead |
| M11 | Load 200, chaos, scans, threat model, tabletop scripts | W-C |

Order: contracts and core on main first; then workstreams; merge A-F; `make check` after each merge.

All milestones merged on main; see STATUS.md for state and evidence.

## Review follow-ups (section 5 reviews, 2026-11-27; reviews/*.md)

### Critical/High addressed only partly, because they need keys or design (top of the queue)
1. R3 C2: no live voice path. The LiveKit worker entrypoint raises and the call loop runs in the dispatcher process. Build the worker-side loop, dispatch the call to it after the clearance commits, and run the 20 test calls (M8). Claims now say 0 real calls.
2. R3 H2: batch provider interfaces and a full LLM reply before TTS will miss 800/1,500 ms. Stream STT/TTS, and render the state machine's chosen act from templates so the LLM leaves the hot path; any real-LLM deviation or 3 s timeout ends the call today.
3. R3 H3/H5: Sarvam returns no confidence (production now refuses stt=sarvam, D-103); barge-in 260 ms is a model constant. Calibrate on real audio.
4. R1 H1: no CCaaS queue in production (AV-CCAAS-1); the demo's staffed queue is now labelled as modelled.
5. R1 H3: read Zendesk ticket status back to compute resolution time (estimate 2 days); until then Agoda's Zendesk report is the source.
6. R1 H5 (rest): idempotent CRM writes and a dead-letter queue (S5). A CRM outage no longer erases a handoff; it pages a person.
7. R2 H3 (rest): ship logs to an India store with 180-day retention; NTP on hosts. SECURITY.md C-12 now says config floor only.
8. Helm: add LiveKit server, SIP service and Redis; voice-worker `__main__`; termination grace period for live calls.

### Mediums
- R1: one pilot timeline with a sample-size estimate (letter aligned to the proposal; power calculation still open); suppression against Agoda's own outbound/opt-out lists; parse the customer's callback time and cap it before the payment deadline; S4 weekly review automation; per-queue handoff SLAs set by Agoda instead of the legal floor.
- R2: rate limiting on the engine and a limiter that trusts only the proxy's forwarded address; append-only audit log and failed sign-in logging; `environment` defaulting to `dev` enables dev tokens; console sessions hold raw API keys with optional expiry; nomination and grievance rights requests; full booking IDs visible to read-only users and MCP under a "redacted" label.
- R3: OpenTelemetry declared but unused, metrics stop at HTTP; `latency_ms` per call measures something other than the gate; transcripts keep full agent lines after barge-in; the TTS-failure apology cannot be heard; Kafka publish blocks up to 10 s inside a DB transaction; LLM cost hard-coded to 0; "ruko" / "ek minute" treated as backchannel; docker-compose lacks SIP.

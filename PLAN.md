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

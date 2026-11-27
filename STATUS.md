# Status (2026-11-27)

Real-provider test calls used: 0 / 20 (no provider keys in the environment).

| M | State | Evidence |
|---|-------|----------|
| M0 | done | PLAN.md, DECISIONS.md (D-001..D-016, D-1xx..D-3xx), docs/discovery-questions.md (31 items) |
| M1 | done | contracts/schemas -> pydantic + TS + OpenAPI, drift check in `make check`; Alembic migration with drift e2e. `make up` written, not run (Docker Hub 429) |
| M2 | done | every REQ in docs/compliance.md has a passing test (test_m2_gate); 10,000-example state-machine proof vs independent oracle (pass, 7 min in full suite); forgery tests; Postgres concurrency e2e |
| M3 | done (mock LLM, scripted caller) | `make eval`: 189 conversations, guardrails 100%, critical personas 100%, J1 link consent 100%, containment 60.3% |
| M4 | done | 1,000 bookings: 91 in holdout bucket, 0 holdout dials, 814 cleared dials, caps and cooldown honoured |
| M5 | done | post-call + encrypted redacted transcripts, Zendesk adapter, handoff summaries, kill switch < 5 s; integrated pipeline test through app/wiring |
| M6 | done (functions); real data needs a pilot | lift with 95% CI, recovery, resolution time, CSAT port, cost per contact |
| M7 | done | console with RBAC; 23 Playwright tests |
| M8 | blocked: no keys | audio evals run on the mock codec + line simulator only (D-105) |
| M9 | done | marketing site + 17 docs pages; disclaimer on every page |
| M10 | partial | Helm chart (not linted: get.helm.sh blocked), migrate Job, retention CronJob; docs/sizing.md (orchestration measured, media/model estimated) |
| M11 | done for mock scope | `make load` 200 sessions; `make chaos` 11 tests (STT/TTS/LLM/telephony/WhatsApp/bus/Postgres); `make scan` green; threat model; tabletop scripts |

Latest report: reports/<ts>-text/index.html (gitignored; regenerate with `make eval`).

## Brief v3 (local session, 2026-11-27)

CI: GitHub Actions does not run on this repo (D-026); every gate below was run locally before push.

| Item | State | Evidence |
|------|-------|----------|
| S10 /demo | done (text mode) | 6 scenarios on the real engine, paced live timeline, kill switch (D-022..D-024). `server/tests/demo` 12 tests; `web/tests/demo` 8 Playwright tests against uvicorn + `next start` |
| Gates | green | `make check` (lint, mypy, 604 tests, tsc, eslint, no contract drift), `make e2e` 8 passed on local Postgres 16 |

## Evals (2026-11-27, branch v3/w3-frontend = main + /demo)

Method: `make eval` and `make eval-audio`, deterministic scripted caller and mock agent LLM (D-007); audio through the mock codec and line simulator with the timing model (D-105). These numbers prove the guardrail and tool layer, not real-LLM or real-audio behaviour. Reports: `reports/20261127T085711Z-text/`, `reports/20261127T085711Z-audio/` (gitignored; regenerate with the same commands).

| Metric | Text (189 conversations) | Audio (378, 4 line profiles) | Target (brief 11.8) |
|--------|------|-------|--------|
| Guardrail rate | 100% | 100% | >= 95% |
| Critical personas C-06/07/08/11/16/17/18 | 100% | 100% | 100% |
| J1 link consent, cooperative | 100% | 95.4% | >= 90% |
| Task success | 100% | 96.8% | reported |
| Containment | 60.3% | 57.1% | reported (pilot target 35-55%) |
| End of speech to first audio p50/p95 (simulated) | n/a | 725 / 950 ms | < 800 / < 1,500 ms |
| Barge-in stop (simulated) | n/a | 260 ms | < 300 ms |
| False interruption / false cutoff C-02, C-25 | n/a | 0% / 0% | < 5% / < 3% |
| WER clean / 3G / street / TV | n/a | 0 / 7.2% / 6.1% / 0 | benchmark is Agoda's audio [CD] |
| Dark-pattern findings | 0 | 0 | 0 |

Regression check: the text scorecard is identical to the run on main of 2026-11-25; the only voice-package change since then is the exported `HANDOFF_QUEUES` constant.

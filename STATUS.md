# Status

Real-provider test calls used: 0 / 20 (no provider keys in the environment).

| M | State | Evidence |
|---|-------|----------|
| M0 | done | PLAN.md, DECISIONS.md (D-001..), docs/discovery-questions.md |
| M1 | done | contracts/schemas -> pydantic + TS, drift check in `make check`; `make up` written but not run (Docker Hub 429) |
| M2 | done for W-A REQs; final REQ-coverage check runs after W-BC merges | 10,000-example state-machine proof vs independent oracle (3m19s, 4 shards); forgery tests; Postgres concurrency e2e |
| M3 | in progress (W-BC) | |
| M4 | done | 1,000 seeded bookings: 91 in holdout bucket, 0 holdout dials, 814 dials all with consumed clearances, caps and 24 h cooldown honoured |
| M5 | done except call-runner wiring | postcall, Zendesk adapter, handoff summaries, kill switch < 5 s test |
| M6 | done (functions); fed by eval data after W-BC | two-proportion lift with 95% CI, recovery, resolution time, CSAT port, cost per contact |
| M7 | done | console with RBAC, 23 Playwright tests |
| M8 | blocked: no keys | |
| M9 | done | marketing site + 17 docs pages |
| M10 | partial | Helm chart written, not linted (get.helm.sh blocked); sizing waits on `make load` |
| M11 | partial | `make scan` green; threat model; tabletop scripts; load and chaos with W-BC |

## Known gaps
- `make up` not exercised: Docker Hub rate-limited the Redpanda and LiveKit images.
- Helm chart not linted.
- Next.js pinned at 15 per brief; postcss overridden to 8.5.33 to clear the high-severity advisory.

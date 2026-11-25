# Handoff from the cloud session (2026-11-24)

Three brief-v3 workstreams were stopped by the usage limit. Their committed work is on
branches; their uncommitted work is in the patches here (never committed because it has
not passed `make check`).

| Branch | Scope | Uncommitted patch |
|--------|-------|-------------------|
| v3/w1-providers-crm | S3 Plivo/Exotel via LiveKit SIP, Meta WhatsApp, LiveKit bridge; S5 CRM loop, webhooks | v3-w1-providers-crm.uncommitted.patch (agent: tests passing, migration for 2 new tables not yet written) |
| v3/w2-qa-costs-concierge | S4 QA loop, S6 costs/numbers, S9 concierge, S10 demo API | v3-w2-qa-costs-concierge.uncommitted.patch |
| v3/w3-frontend | Section 6 redesign, pages, console, concierge UI, /demo, /agoda | none (2 commits on the branch) |

Resume a stream locally:

```bash
git checkout v3/w1-providers-crm
git apply handoff/v3-w1-providers-crm.uncommitted.patch
make hooks
make check
```

All three branches start before S1/S2/S7 landed on main; merge main into each before
finishing. Any new table needs `tenant_id` and `rls.enable()` in its migration
(tests/e2e/test_tenant_isolation.py fails otherwise).

State of main: see STATUS.md and DECISIONS.md (D-017..D-021). Remaining v3 work: S7 rest
(concurrency and rate limits, envelope encryption, retention report), S8, S11, section 5
reviews, final summary.

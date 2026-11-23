# Threat model (M11)

Method: STRIDE over the data flow booking_event -> gates -> dial -> agent -> WhatsApp -> outcome/handoff.

| # | Threat | Asset | Mitigation | Test |
|---|--------|-------|------------|------|
| T-01 | Spoofed dial bypassing gates (Elevation) | Telecom licence, customers | GateClearance minted only by `evaluate`; InitVar token; DB single-use row; import-linter on `telephony.dial` | test_clearance_unforgeable, test_static_proofs, e2e concurrency |
| T-02 | CLI spoofing (Spoofing) | Caller identity | `dial` has no CLI parameter; CLI from clearance | test_req_cli_01 |
| T-03 | Prompt injection makes agent move money (Tampering) | Revenue, customer | Tool allowlist outside the LLM; no money tools exist | test_req_* voice suites, persona C-16 |
| T-04 | Card/OTP captured in transcripts (Information disclosure) | Payment credentials | Redaction before LLM and storage; logger redaction; no card fields | test_req_pay_01, test_static_proofs |
| T-05 | Stolen API token (Spoofing) | Console, kill switch | Bearer tokens from secret store; prod rejects dev tokens; least-privilege roles; every privileged action audited | tests/admin, test_req_dpdp_09 |
| T-06 | Kill switch fails to stop dials (Denial of control) | Compliance | Gate + re-check inside dial transaction; dispatcher drops queue | test_killswitch_latency |
| T-07 | Complaint storm leads to TRAI bar (Repudiation/availability) | Number resources | House rule pauses at 1 (CLI) and 2 (all) | test_req_trai_06 |
| T-08 | Out-of-India processing (Information disclosure) | Personal data | Prod validator on provider regions | test_req_dpdp_09 |
| T-09 | Audit log tampering (Repudiation) | Evidence | Append-only table, mirrored to Kafka `av.audit.v1` (180 d) | test_req_dpdp_10 |
| T-10 | Holdout contamination (Tampering with measurement) | Lift validity | Holdout gate first; hash of fixed salt; never overridden | test_holdout, proof |
| T-11 | Provider outage silently degrades behaviour | Customer experience | Typed errors; no provider switch; apology + human callback | tests/chaos |
| T-12 | Dependency compromise (Supply chain) | Code | Lockfiles (uv.lock, package-lock.json), `make scan` in CI | CI |

Residual risks are in the session summary and STATUS.md.

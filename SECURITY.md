# Security controls (REQ-SEC-01)

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.

Until Booking Holdings' supplier code, security questionnaire and privacy
addendum are available [CD], we build to the strictest common baseline.

| ID | Control | Implementation | Verified by |
|----|---------|----------------|-------------|
| C-01 | Audit log for every privileged action | `core/audit.write_audit`; append-only `audit_log` + `av.audit.v1` | tests/compliance, tests/admin |
| C-02 | Least-privilege RBAC (admin, ops, auditor, read_only) | `admin/rbac.py` | tests/admin |
| C-03 | Encryption in transit | TLS at ingress (Helm), Kafka TLS, Postgres `sslmode=verify-full` in production values | deploy/helm review |
| C-04 | Encryption at rest | Postgres volume encryption (platform) plus field-level Fernet for transcripts and audio refs | tests/postcall |
| C-05 | No training on client data | Contract term with every subprocessor; no training code path exists | docs/subprocessors.md |
| C-06 | Processing record per purpose | `docs/dpia-inputs.md`; x-purposes on every field | test_req_dpdp_02 |
| C-07 | PII redaction at write time and in logs | `core/redaction.py`, `core/logging.JsonFormatter` | test_req_pay_01, tests/core |
| C-08 | No card data anywhere | Static proof over contracts and tables | test_static_proofs |
| C-09 | Only declared CLIs; single-use clearances | `compliance/evaluate`, `telephony/dial` | test_clearance_unforgeable |
| C-10 | Kill switch < 5 s | `compliance/killswitch`, `/killswitch` | tests/api/test_killswitch_latency |
| C-11 | Secrets never in repo or config files | Secrets from the platform secret store; production validator rejects dev tokens and pepper | test_req_dpdp_09 |
| C-12 | ICT logs 180 days, producible within India, NTP to NIC/NPL | `retention.ict_log_days >= 180`, `ntp_servers` | test_req_sec_03 |
| C-13 | CERT-In report within 6 h of noticing | `incidents/service.py` (`cert_in` window) | test_req_sec_02 |
| C-14 | Dependency and secret scans | `make scan` (pip-audit, npm audit, gitleaks-style regex scan) | CI |
| C-15 | Threat model | `docs/threat-model.md` | review |

## Reporting a vulnerability
Email security@prosperops.example [placeholder]. Do not open a public issue.

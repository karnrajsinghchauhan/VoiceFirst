# Kafka topics

All topics speak the Kafka API (Redpanda locally, Agoda Kafka in production).
Values are JSON validated against the named schema; every record carries
`schema_version`, `tenant_id`, `trace_id`.

| Topic | Key | Value schema | Retention | Producer | Notes |
|-------|-----|--------------|-----------|----------|-------|
| av.booking-events.v1 | booking_id | booking_event.json | 7 days | ingest (campaigns) | Source events from Agoda |
| av.gate-decisions.v1 | booking_id | gate_decision.json | 180 days | compliance.evaluate | Immutable; one per evaluation |
| av.call-outcomes.v1 | booking_id | call_outcome.json | 180 days | postcall | No raw transcript; redacted only |
| av.handoffs.v1 | booking_id | handoff_summary.json | 30 days | handoff | Feeds Zendesk / CCaaS |
| av.complaints.v1 | cli_e164 | complaint.json | 365 days | compliance.complaints | DLT-forwarded complaints |
| av.audit.v1 | target | audit_event.json | 180 days minimum (REQ-SEC-03) | core.audit | Append-only |

Retention of 180 days on decision, outcome and audit topics matches the CERT-In
ICT log requirement; Postgres is the system of record for longer retention.

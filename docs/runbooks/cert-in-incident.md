# Runbook: CERT-In reportable incident (REQ-SEC-02)

Clock: the report is due within 6 hours of noticing the incident. The timer
starts at `detected_at`, which is when anyone first noticed it, not when the
record was created.

1. Open the incident: `POST /incidents {kind: "cert_in", severity, summary, detected_at}`. The response carries `report_due_at`.
2. If any personal data may be affected, open a second incident with `kind: "dpdp_breach"` (72 h Board report; notify principals without delay).
3. If calls could be affected, engage the kill switch (`POST /killswitch`), reason "incident <id>".
4. Preserve evidence: export `audit_log`, `gate_decisions`, `dial_attempts` for the window; ICT logs are kept 180 days within India.
5. Fill the CERT-In form (types of incident per the 28 Apr 2022 Directions) and send it to Agoda's designated point of contact [CD] for submission. Record `reported_at` with `POST /incidents/{id}/reported`.
6. Post-incident review within 5 working days; add the test that would have caught it (rule 6.8).

Tabletop script: `docs/runbooks/tabletop-cert-in-dpdp.md`.

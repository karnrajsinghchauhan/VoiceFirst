# DPIA inputs (REQ-DPDP-10)

Prepared in case Agoda is notified as a Significant Data Fiduciary [CD].

1. Processing record per purpose: J1 payment rescue (transaction basis), J2 booking confirmation (service). Fields read per purpose are the `x-purposes` tags in `contracts/schemas/booking_event.json`.
2. Data categories: first name, phone number, booking reference (masked when spoken), property city/name, stay dates, guest count, amount due, preferred language, WhatsApp opt-in, VIP and minor-suspected flags. No card, UPI or OTP data is collected or stored (REQ-PAY-01).
3. Retention: audio 30 days, redacted transcripts 180 days, consent records [CD], ICT logs 180 days.
4. Audit logs: `audit_log` table and `av.audit.v1`; every privileged action with actor, role, reason.
5. Model-risk notes: the LLM proposes utterances and tool calls; deterministic guardrails (tool allowlist, handoff triggers, opt-out, redaction, dark-pattern filter) run outside the model and can override it. No training or fine-tuning on client data. Evaluated per release on 30 personas with a regression gate (brief 11.9).
6. Residency and subprocessors: `docs/subprocessors.md`.

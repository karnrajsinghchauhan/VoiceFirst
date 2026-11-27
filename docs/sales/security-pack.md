# Security pack: Agoda Voice

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.
Version 1.0, 27 November 2026. Engineering description, not legal advice. Items marked [CD] are confirmed in discovery.

## 1. Certification status (plainly)
| Framework | Status |
|---|---|
| SOC 2 Type I / II | Not held. Readiness in progress; controls below map to the Trust Services Criteria. No audit booked. |
| ISO/IEC 27001 | Not held. Not planned before a pilot. |
| PCI DSS | Out of scope by design: no card data is collected, stored or transmitted (payment happens on Agoda's hosted page). |
| OWASP ASVS | Level 2 used as the engineering checklist; self-assessment in progress. |
| Penetration test | Not yet performed by a third party. Offered before go-live at our cost if Agoda requires it ([CD]: Agoda's preferred firm). |

## 2. Data flow
```
Agoda Kafka (booking events)
   -> engine (India region): holdout -> 11 compliance checks -> single-use clearance
   -> telephony provider (India PoP)  <-> customer's phone
   -> speech to text (redaction of card numbers and OTPs happens here, before any model)
   -> language model (redacted text + purpose-limited booking fields only)
   -> text to speech -> customer
   -> WhatsApp utility template (Agoda-hosted link) -> customer
   -> outcome + encrypted redacted transcript -> Postgres (India) -> Kafka outcomes topic
   -> case / handoff summary -> Agoda CRM (Zendesk) -> Agoda human agent
```
The agent reads only fields tagged for the call's purpose (REQ-DPDP-02); a static test fails if any field lacks a purpose tag. The full booking ID, email address and card data are never spoken; at most the last four characters of the booking ID.

## 3. Controls
The control list lives in `SECURITY.md` (C-01 to C-15). Summary:

| Area | Control |
|---|---|
| Identity and access | Roles admin, ops, auditor, read-only; SSO through Agoda's OIDC provider; scoped, rotatable API keys stored as SHA-256 hashes; production refuses static tokens |
| Audit | Append-only audit log of every privileged action (actor, role, reason), also published to Kafka |
| Encryption | TLS in transit (ingress, Kafka, Postgres verify-full); volume encryption plus field-level encryption of transcripts and audio references |
| Tenant isolation | One runtime per tenant; Postgres row-level security on every table; production refuses a superuser database role |
| Data minimisation | Purpose tags on every field; redaction at write time and in logs; no card fields anywhere in contracts (static proof) |
| Calling safety | Single-use clearances that only the compliance module can construct; one function can dial, enforced by an import rule |
| Kill switch | One authenticated call stops new dials in under 5 s (tested) |
| Supply chain | Pinned dependencies; `make scan` (pip-audit, npm audit, secret scan) |
| Model use | No training or fine-tuning on client data, in code and as a contract term with every sub-processor |

## 4. Sub-processors
See `docs/subprocessors.md`. Pilot defaults: Sarvam (speech, India [CD: confirm region]), one LLM provider (region [CD]), Plivo or Exotel (telephony, India), Meta WhatsApp Cloud API (outside India), Zendesk (Agoda's tenant). The production config refuses to boot if a provider's region is outside Agoda's allowlist ([CD]; default India).

## 5. Retention (defaults; configurable per purpose)
| Data | Default | Basis |
|---|---|---|
| Call audio | 30 days | REQ-DPDP-07 |
| Redacted transcripts | 180 days | REQ-DPDP-07 |
| Call outcomes | Pseudonymised on erasure, kept for lift measurement | D-302 |
| Consent and opt-out records | As the law requires [CD: counsel] | D-302 |
| ICT logs | 180 days rolling, producible in India: a deployment requirement (log shipping to an India store and host NTP), not yet built | CERT-In Directions (S-29) |
A nightly purge deletes expired data and logs the counts.

## 6. Incident response
| Clock | Obligation | How we meet it |
|---|---|---|
| Detection | `detected_at` recorded on every incident | `incidents/service.py` |
| 6 hours | CERT-In report for listed incidents | Timer from detection; runbook and report template |
| 72 hours | Detailed DPDP Board report for a personal-data breach (Agoda as fiduciary; we notify Agoda first, within 24 hours) | Timer; drafted report |
| Without delay | Notify affected data principals (Agoda decides content) | Template and WhatsApp/SMS path |
| Any time | Kill switch | Operator access for Agoda from day one |
Runbooks: `docs/runbooks/`. Tabletop scripts for CERT-In and DPDP exist; no live incident has occurred.

## 7. Security questionnaire: answer sheet
| # | Question | Answer |
|---|---|---|
| 1 | Do you hold SOC 2 or ISO 27001? | No. SOC 2 readiness in progress; no audit booked. |
| 2 | Where is data processed and stored? | India region by default; out-of-India sub-processors are listed and need Agoda's approval. |
| 3 | Is customer data used to train models? | No, in code and by contract with every sub-processor. |
| 4 | Do you store card data? | No. Card numbers and OTPs are redacted from speech before any model or storage. |
| 5 | How is access controlled? | RBAC with four roles, SSO via Agoda's IdP, scoped API keys, least privilege. |
| 6 | Is MFA enforced? | Through Agoda's IdP for console users; API keys are scoped and rotatable. |
| 7 | Are privileged actions logged? | Yes, append-only with actor, role and reason; exportable. |
| 8 | Encryption in transit and at rest? | TLS 1.2+ in transit; volume plus field-level encryption at rest. |
| 9 | Key management? | Platform secret store; per-tenant envelope encryption is planned (S7) and a production KMS is [CD]. |
| 10 | Tenant isolation? | Separate runtime per tenant plus Postgres row-level security. |
| 11 | Vulnerability management? | Dependency and secret scans on every change; patch within 7 days for critical findings (target). |
| 12 | Penetration testing? | None yet by a third party; offered before go-live. |
| 13 | Incident response timelines? | 24 h to Agoda; supports CERT-In 6 h and DPDP 72 h. |
| 14 | Backups and restore? | Managed Postgres point-in-time recovery (pilot host [CD]); restore drill to be recorded before go-live. |
| 15 | Business continuity? | Kill switch; stateless engine; failure mode is "no call", never a degraded call. |
| 16 | Sub-processor changes? | 30 days' notice and a right to object (DPA). |
| 17 | Data deletion on exit? | Within 30 days of termination, with a deletion certificate. |
| 18 | Rights requests (access, correction, erasure)? | Workflow with SLA timers (48 h acknowledgement, 30 days resolution by default). |
| 19 | AI transparency? | First sentence discloses AI and recording; recordings carry a provenance hash and model ids. |
| 20 | Can the AI take actions with financial effect? | No. Ten allowlisted tools; none moves money. |
| 21 | Human oversight? | Warm transfer on defined triggers; disputes always go to a person. |
| 22 | Telecom compliance? | Declared caller IDs, consent basis, DND check, call window, caps, complaint pauses; counsel sign-off pending. |
| 23 | Background checks for staff with access? | [CD]: founder-run today; checks will be completed for anyone given production access. |
| 24 | Secure development? | Typed code, mandatory checks before every commit, tests for every compliance rule, reviewed pull requests. |
| 25 | Insurance? | [CD]: cyber and professional indemnity cover to be quoted before signature. |

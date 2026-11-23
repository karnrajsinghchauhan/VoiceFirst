# Compliance requirements

This document is engineering guidance, not legal advice. Indian counsel must
sign it off before go-live [CD]. Every REQ below has a test at
`server/tests/compliance/test_<req_id>.py`; a REQ without a passing test blocks
M2.

## TRAI: TCCCPR 2018 as amended (Second Amendment Feb 2025; Third Amendment 05 of 2026, notified 18 Sep 2026)
| REQ | Rule | Where enforced |
|-----|------|----------------|
| REQ-TRAI-01 | Every outbound call is A2P; the CLI needs a2p_declared, declaration_ref, OAP, dlt_recorded_at | `gates.gate_cli_declared` |
| REQ-TRAI-02 | Service/transactional calls use configured 1600xx/1601xx; promotional (J7) only 140xx | `gates.gate_series` |
| REQ-TRAI-03 | Consent basis recorded; explicit consent 7 days or until revoked; inquiry 7 days | `gates.gate_consent`, `consent.expiry_for` |
| REQ-TRAI-04 | Preference registry before every dial; BLOCK PROMO blocks promotional only; house rule: any DND blocks J2/J7; J1 only with recorded legal sign-off | `gates.gate_dnd`, `compliance.dnd_j1_transaction_signoff_ref` [CD] |
| REQ-TRAI-05 | Opt-out -> mark_dnc, confirm once, end; no consent re-request for 90 days | `consent.mark_dnc`, `consent.assert_may_request_consent`, `gates.gate_opt_out_lock` |
| REQ-TRAI-06 | Any complaint pauses the CLI; 2 unique in 10 days pause all and page | `complaints.ingest_complaint` |
| REQ-TRAI-07 | 09:00-21:00 recipient local time; narrower allowed, never wider. Legal source [CD]; applied as house policy | `gates.gate_window`, `config.CallWindow` |
| REQ-TRAI-08 | <= 2 attempts per event; >= 24 h per number; <= 1 WhatsApp fallback per event | `gates.gate_cap_cooldown`, `whatsapp.send_no_answer_fallback` |
| REQ-TRAI-09 | Pilot dials +91 only | `jurisdiction.IndiaPolicy` |
| REQ-TRAI-10 | Complaint ingest accepts DLT-forwarded complaints incl. call-management-app reports | `contracts/schemas/complaint.json` |

## Telecommunications Act 2023
REQ-TEL-01: TCCCPR is the operative rulebook. Section references for consent,
DND and complaints under the Act: [CD: counsel to supply]. No separate code path.

## DPDP Act 2023 and DPDP Rules 2025 (notified 13 Nov 2025)
Consent Manager provisions apply from 13 Nov 2026; core duties and penalties
from 13 May 2027. We build to the full standard now.
| REQ | Rule | Where enforced |
|-----|------|----------------|
| REQ-DPDP-01 | First utterance names purpose and recording; WhatsApp notice link carries the itemised notice | `voice/prompts`, `voice/notice.py`, `messaging/templates.py` |
| REQ-DPDP-02 | Every contract field tagged with purposes (x-purposes); context builder reads only allowed fields | `voice/context.py` |
| REQ-DPDP-03 | Withdrawal in one sentence or one WhatsApp reply | `voice/guardrails.py`, `messaging/inbound.py` |
| REQ-DPDP-04 | Child on the line -> ask for booker, else end without discussing; log minor_on_line | `voice/guardrails.py` |
| REQ-DPDP-05 | Rights requests with SLA timers | `rights/` |
| REQ-DPDP-06 | Breach: detected_at; Board report within 72 h; principals notified without delay | `incidents/service.py` |
| REQ-DPDP-07 | Retention: audio 30 d, transcripts 180 d, consent records [CD]; nightly purge logs counts | `postcall/retention.py` |
| REQ-DPDP-08 | consent_record has consent_manager_id and artefact_ref | `contracts/schemas/consent_record.json` |
| REQ-DPDP-09 | India residency by default; production validator rejects out-of-allowlist regions | `core/config.validate_for_environment`, `docs/subprocessors.md` |
| REQ-DPDP-10 | If Agoda is an SDF [CD]: DPIA inputs, audit logs, model-risk notes | `docs/dpia-inputs.md` |

## IT Act 2000 and CERT-In Directions (28 Apr 2022)
| REQ | Rule | Where |
|-----|------|-------|
| REQ-SEC-01 | Control list | `SECURITY.md` |
| REQ-SEC-02 | CERT-In report within 6 h of noticing; timer from detection | `incidents/service.py` |
| REQ-SEC-03 | ICT logs 180 days rolling, producible in India, NTP synced to NIC/NPL | `core/config` (`retention.ict_log_days`, `ntp_servers`), `contracts/kafka-topics.md` |

## Synthetic voice and AI disclosure
| REQ | Rule | Where |
|-----|------|-------|
| REQ-AI-01 | IT Amendment Rules 2026 (G.S.R. 120(E)); scope [CD]; we disclose regardless. First utterance says "AI assistant"; recordings carry ai_generated=true, model ids, provenance hash | `call_outcome.json`, `voice/` |
| REQ-AI-02 | Stock voices licensed for telephony only; Hindi verb gender matches the voice | `docs/licences.md`, prompt lint |
| REQ-AI-03 | Never claims to be human | `voice/guardrails.py` |

## Payments (RBI, PCI DSS v4.x, NPCI)
| REQ | Rule | Where |
|-----|------|-------|
| REQ-PAY-01 | Never collect/repeat/store card, CVV, expiry, UPI PIN, OTP, netbanking creds; redact STT before LLM and storage | `core/redaction.py`, `voice/guardrails.py` |
| REQ-PAY-02 | Payment only via Agoda-hosted link over WhatsApp; no UPI collect; no card storage; out of PCI scope. Link format/expiry [CD] | `messaging/whatsapp.py` |
| REQ-PAY-03 | Read-back equals booking.amount_due, same currency, Indian numbering | `voice/normalise.py` |

## Consumer Protection Act 2019, E-Commerce Rules, Dark Patterns Guidelines 2023
| REQ | Rule | Where |
|-----|------|-------|
| REQ-CP-01 | None of the 13 CCPA dark patterns in any script or template; binding from 1 Jan 2027 (G.S.R. 789(E)) with yearly self-audit | `voice/dark_patterns.py`, eval suite 11.6 |
| REQ-CP-02 | Full payable amount stated once from the booking; no added items, no invented scarcity, no repeated refused ask | `voice/guardrails.py` |
| REQ-CP-03 | Every outcome carries the grievance channel; case SLA fields 48 h ack and 30 days resolution | `call_outcome.grievance_channel`, `handoff_summary.sla_*` |

## WhatsApp Business Platform
| REQ | Rule | Where |
|-----|------|-------|
| REQ-WA-01 | Templates only to numbers with recorded opt-in (source, timestamp) | `whatsapp._assert_opted_in` |
| REQ-WA-02 | Utility only in pilot; cost model assumes every template is paid (Rs 0.1150 + 18% GST) | `messaging/templates.py`, `whatsapp.template_cost_paise` |
| REQ-WA-03 | Free-form only inside 24 h window; quality "low" pauses WhatsApp and pages | `whatsapp.send_free_form`, `whatsapp.poll_quality` |

## Caller identity
REQ-CLI-01: only the declared CLI is ever shown; `telephony.dial` takes the CLI
from the single-use clearance and has no CLI parameter. CNAP and Truecaller
business verification [CD].

## Other jurisdictions
`JurisdictionPolicy` has one implementation, `IndiaPolicy`. SG PDPA + DNC,
TH PDPA, MY PDPA (amended 2024), US TCPA (FCC Feb 2024: AI voices are
"artificial"), EU GDPR + ePrivacy and AI Act Art. 50: details [CD].

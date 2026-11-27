# Proposal: Agoda Voice pilot for India

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.
Version 1.0, 27 November 2026. Supersedes `docs/proposal-draft.md` (branch v3/w2). Every number is sourced (docs/sources.md), measured on test data with its date, or labelled estimate. Commercial terms are an offer for discussion and become binding only in a signed agreement.

## 1. Executive summary
Agoda already runs AI across support, keeps people in charge of outcomes and measures resolution time and CSAT (docs/sources.md S-07). This proposal adds one layer for one market: outbound service calls in Hindi, English and Hinglish that rescue failed or pending payments and confirm bookings before arrival, under India's telecom and data-protection rules, with the effect measured against a 10% no-call holdout. We run it for eight weeks as a managed service. If it works, Agoda chooses between a retainer and taking the system onto its own infrastructure.

## 2. Statement of work (pilot)
### 2.1 In scope
| Item | Detail |
|---|---|
| J1 payment rescue | Bookings with `payment_failed`, or `payment_pending` past the agreed threshold, India (+91) numbers only |
| J2 pre-arrival confirmation | Confirm check-in date and time, guests, special requests; answers only from the booking record; no offers |
| Holdout | 10% of eligible bookings, fixed salt per experiment, decided before any check, never overridden |
| Channels | Outbound voice from declared caller IDs; WhatsApp utility templates to opted-in numbers |
| Integrations | Agoda Kafka topic for booking events (read); Zendesk or the agreed CRM for cases (write); warm transfer to Agoda's contact centre or a callback queue |
| Reporting | Weekly review of every failed or low-scoring call; final written result with the lift estimate |

### 2.2 Out of scope for the pilot
Inbound support, supply calls, analytics on Agoda's contact history, any promotional call or message, any call outside India, any action that moves money.

### 2.3 Responsibilities
| ProsperOps | Agoda |
|---|---|
| Build, host and operate the service in an India region | Answer the discovery questions (docs/discovery-questions.md) |
| Caller-ID declaration and DLT paperwork as Agoda's agent, if Agoda's category allows | Name the sender entity and approve caller IDs and templates |
| Weekly review, fixes through reviewed pull requests, eval gate on every change | Provide a sandbox Kafka topic, CRM sandbox and a sample of call audio |
| Security pack, DPA, incident response to the agreed timelines | Counsel sign-off on docs/compliance.md before the first live call |

### 2.4 Timeline
| Week | Work | Exit criterion |
|---|---|---|
| 1 | Discovery answers; success metrics and thresholds signed; DLT and template submissions | Signed success criteria |
| 2 | Kafka and CRM connected in sandbox; counsel review | Sandbox call end to end |
| 3 | Evaluation on Agoda's audio sample; internal test calls (Agoda staff phones only) | Guardrails 100% on critical personas; latency targets met on real audio |
| 4 | Live at 5% of eligible bookings, holdout running | No compliance incident in 5 days |
| 5-6 | Ramp to 100% of eligible bookings | Complaint rate under the agreed ceiling |
| 7 | Lift read-out | Report delivered |
| 8 | Decision: continue, change or stop | Signed decision |

### 2.5 Success criteria (agreed in week 1; illustrative thresholds below)
| Measure | Method | Illustrative threshold (to agree) |
|---|---|---|
| Payment recovery lift | Intention-to-treat over all J1-eligible bookings, called vs holdout, two-proportion test, 95% CI (D-202) | Lower bound of the CI above 0 |
| Compliance | Gate decision written for every dial; complaints per 1,000 calls | Zero dials without a clearance; complaint rate under the agreed ceiling |
| Customer experience | CSAT by WhatsApp survey; resolution time for transferred calls, from Agoda's Zendesk report on the tickets we open (each call records its ticket id). Automatic read-back of ticket status is a week-2 task (estimate: 2 days) | No worse than the matching human baseline |
| Cost | Cost per resolved contact from the cost book | Reported; no threshold in the pilot |

## 3. Commercials
| Item | Terms |
|---|---|
| Pilot fee | USD 20,000 fixed for 8 weeks |
| Payment | 50% (USD 10,000) on signature. 50% (USD 10,000) at risk: payable only if the payment-recovery lift's 95% CI lower bound is above zero, or as otherwise agreed in week 1 |
| After the pilot, option A | USD 6,000 per month retainer plus Rs 25 per AI-resolved contact |
| After the pilot, option B | USD 0.09 per outbound minute, all in |
| Build-operate-transfer | At any point after the pilot, Agoda may take the system onto its own Kubernetes with a handover of code, runbooks and training; fee quoted as a fixed project (estimate: 4-6 weeks of work) |
| Pass-through costs | Telephony, WhatsApp and model usage are included in options A and B; in the pilot they are included up to an agreed call volume (estimate: 20,000 calls) |
| Taxes | Exclusive of GST and withholding |

"AI-resolved contact" (the billing unit): a J1 call after which the booking is paid within its payment window, or a J2 call ending `details_confirmed`; in both cases with no transfer to a person and no complaint within 7 days. A link sent that is never paid, an opt-out, or a callback is not billed. (The engine's containment metric, `AI_RESOLVED` in `analytics/metrics.py`, counts goals met on the call; it is reported, not billed.)

### 3.1 Our cost to serve (estimate, for transparency)
From the cost book on branch v3/w2 (`config/costs.yaml`), prices as of 2026-11-23, re-check before quoting: about Rs 2.72 per call minute and about Rs 5.44 per 2-minute call, all components included (estimate). Speech-to-text and text-to-speech prices are Sarvam's published pay-as-you-go rates (docs/sources.md S-31); the WhatsApp rate is reseller-reported (S-30); telephony, LLM and infrastructure lines are estimates.

## 4. Guarantees
- The five promises (docs/sales/one-pager.md) are enforced in code and covered by automated tests that run on every change.
- Kill switch: new dials stop in under 5 seconds; Agoda receives operator access to it from day one.
- If any call is placed without a clearance, we pause the service, report within 24 hours, and the pilot fee's at-risk half is forfeited.

## 5. Case study and reference calls
With Agoda's prior written approval of the text, ProsperOps may: (a) name Agoda as a client; (b) publish an anonymised case study using aggregate results; (c) ask Agoda for up to two reference calls a year. Agoda may refuse any of these without affecting the agreement. No Agoda logo or brand asset is used without a separate written licence.

## 6. Intellectual property
- Agoda owns its data, its configuration values, its prompts' Agoda-specific wording, and every output about its customers.
- ProsperOps owns the platform (engine, tester, console, chart) and grants Agoda a non-exclusive, perpetual licence to use it for its own business if Agoda takes the build-operate-transfer option, including the right to modify it.
- Neither party trains or fine-tunes any model on Agoda's data.

## 7. Liability
- Each party's total liability is capped at the fees paid or payable in the 12 months before the claim (pilot: USD 20,000).
- Carve-outs from the cap: breach of confidentiality, data-protection breach caused by the party's breach of the DPA (capped separately at 2x the 12-month fees), fraud and wilful misconduct, and indemnities for third-party IP claims.
- No liability for indirect or consequential loss.
These positions are a starting point and require legal review by both parties.

## 8. Security and data
See docs/sales/security-pack.md, the DPA template (docs/sales/dpa-template.md) and docs/subprocessors.md.

## 9. Assumptions
- Agoda can supply booking events with the fields in `contracts/schemas/booking_event.json`, or a mapping to them.
- A sender category and caller-ID series exist that permit service calls of this kind (discovery).
- Indian counsel signs off docs/compliance.md before the first live call.

## 10. Roadmap (not priced)
Inbound support (J4), supply calls to Tier-2/3 properties from CSV (J5), contact analytics (J6), promotional offers only with a 140-series caller ID, recorded promotional consent and a dark-pattern audit (J7).

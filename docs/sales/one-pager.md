# Agoda Voice: one page

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.
Prepared 27 November 2026. Numbers are sourced (docs/sources.md), measured on test data with a date, or labelled estimate.

## What it is
Outbound AI service calls to Agoda customers in India, in Hindi, English and Hinglish, for two jobs:

1. **Payment rescue.** A payment failed or is still pending. The agent offers to send an Agoda-hosted payment link over WhatsApp and sends it only after an explicit yes. It never takes card details, UPI PINs or OTPs by voice.
2. **Pre-arrival confirmation.** Two days before check-in it confirms the date, arrival time and guests, and records special requests. It makes no offers.

Every judgement call goes to a person. A fixed 10% of bookings is never called, so the effect is measured, not assumed.

## The pilot
- 8 weeks, India-originating bookings, payment rescue and confirmation, 10% no-call holdout.
- Success measures agreed in week 1: payment recovery against the holdout (95% confidence interval), resolution time and CSAT for calls that reach a person, complaint rate, cost per resolved contact.
- Run by us as a managed service in an India region; the same Helm chart can move onto Agoda's Kubernetes afterwards.

## The five promises
| Promise | How it is enforced |
|---|---|
| The AI never moves money | Ten allowlisted tools; none can refund, cancel, re-price or waive. Money questions become a case and a transfer. |
| A person is one sentence away | "Insaan se baat", disputes, fraud, legal, anger, VIP, emergencies: warm transfer with a five-line summary, or an honest callback. |
| Every call is disclosed and compliant | AI and recording disclosed in the first sentence. Eleven checks (holdout, +91 only, kill switch, consent, DND, opt-out lock, declared caller ID, number series, caller-ID status, call window, caps) before a single-use clearance. |
| Data stays Agoda's | Card and OTP redaction before the model sees text, encryption at rest, no training on client data, India residency by default. |
| One switch stops everything | Kill switch pauses all campaigns and drops queued calls; new dials stop in under 5 s (measured on test data, 2026-11-27). |

## Proof so far (test data, 2026-11-27)
- Compliance proof: a call is placed if and only if all checks pass, 10,000 generated examples.
- Guardrails held in 100% of 189 text conversations and 378 audio-simulated conversations; 100% on refund bait, chargeback, consumer-court, child, prompt-injection, card-number and OTP personas.
- These prove the safety layer on scripted callers and mock models, not real-world performance. The pilot measures that.

## Commercials
- Pilot: USD 20,000 fixed. 50% at signature; 50% at risk against the holdout result.
- After the pilot: USD 6,000 a month plus Rs 25 per AI-resolved contact, or USD 0.09 per outbound minute. Build-operate-transfer option.

## The ask
A 45-minute discovery call with CX and payments, then a sandbox Kafka topic and a sample of call audio for evaluation.

Contact: Karn, founder, [LEGAL_ENTITY_NAME] ([CD]), [CONTACT_EMAIL] ([CD]).

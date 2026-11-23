# Proposal draft: Agoda Voice pilot

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.
Draft for discussion. Every number is sourced (docs/sources.md), measured on test data
(reports/, dated), or labelled estimate.

## Executive summary
An outbound AI calling service in Hindi, English and Hinglish for Agoda's India customers.
It rescues failed and pending payments by sending an Agoda-hosted payment link over
WhatsApp, and confirms bookings before arrival. It never moves money, hands every
judgement call to a human, discloses AI and recording in the first sentence, and
measures its effect against a 10% no-call holdout.

## Scope
- J1 payment rescue and J2 booking confirmation, India (+91) only.
- Phase 2 (not in the pilot): inbound support, supply hunter, contact intelligence,
  promotional connected-trip offers (only with 140-series CLI and DCA consent).

## Timeline (W1-W8)
| Week | Work |
|---|---|
| W1 | Discovery answers ([CD] list), DLT/CLI registration started, data contract sign-off |
| W2 | Kafka and Zendesk integration in Agoda's sandbox; counsel review of docs/compliance.md |
| W3 | 20 internal test calls; audio evals on Agoda's own recordings |
| W4 | Soft launch: 5% of eligible bookings, holdout running |
| W5-W6 | Ramp to 100% of eligible bookings; weekly review and fixes |
| W7 | Lift read-out with 95% CI |
| W8 | Decision: continue, change or stop; transfer plan if continuing |

## Pricing
- Pilot: USD 20,000 fixed, half at risk against the agreed success metric.
- After the pilot: USD 6,000 per month plus Rs 25 per AI-resolved contact, or USD 0.09 per
  outbound minute.
- Containment target: 35-55% (target, not a measurement).

### Our cost to serve (from config/costs.yaml)
<!-- cost-table:start -->
| Component | Unit | Unit price (Rs) | Per minute | Basis | Checked |
|---|---|---|---|---|---|
| telephony | per 30-s pulse | 0.19 | Rs 0.3800 | estimate | 2026-01-01 |
| a2p_termination | per minute | 0.00 | Rs 0.0000 | estimate | 2026-11-23 |
| stt | per minute | 0.49 | Rs 0.4900 | [S-31 Sarvam pay-as-you-go STT](https://www.sarvam.ai/api-pricing) | 2026-11-01 |
| llm | per minute | 0.40 | Rs 0.4000 | estimate | 2026-11-23 |
| tts | per 1,000 characters | 3.00 | Rs 1.2600 | [S-31 Sarvam Bulbul v3; units = agent_tts_chars_per_minute / 1000](https://www.sarvam.ai/api-pricing) | 2026-11-01 |
| orchestration_infra | per minute | 0.10 | Rs 0.1000 | estimate | 2026-11-23 |
| whatsapp | per utility template, before GST | 0.1150 | Rs 0.0678 | [S-30 Meta WhatsApp India utility rate; every template assumed paid (REQ-WA-02); units = templates per call / call minutes](https://developers.facebook.com/docs/whatsapp/pricing) | 2026-10-01 |
| storage_qa | per minute | 0.02 | Rs 0.0200 | estimate | 2026-11-23 |

- Per minute, all components: **Rs 2.7178** (estimate where any line is).
- Per call at 2.0 min (estimate): **Rs 5.4357**.
- Per resolved contact at a 0.55 resolution rate (estimate): **Rs 9.8831**.
- WhatsApp includes GST at 0.18. Prices as of 2026-11-23; re-check before quoting.
<!-- cost-table:end -->

## Guarantees
- The five promises (no money moves, a human one sentence away, disclosed and compliant
  calls, client-owned data, a kill switch under 5 s), each enforced in code and tested.

## Security
See SECURITY.md, docs/threat-model.md and docs/subprocessors.md.

## Metrics
Lift versus holdout (two-proportion test, 95% CI), recovery rate, resolution time, CSAT,
cost per resolved contact, complaint rate.

## Onboarding
What we need from Agoda: docs/discovery-questions.md.

## Roadmap
J4 inbound, J5 supply hunter, J6 contact intelligence, J7 promotional offers.

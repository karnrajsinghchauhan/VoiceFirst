# Discovery call: agenda, questions, business case, objections

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.

## Agenda (45 minutes)
| Min | Item |
|---|---|
| 0-5 | Introductions; what they want out of the call |
| 5-15 | Their current India contact volumes, payment failure flow and how outbound is handled today |
| 15-25 | Live demo: failed UPI payment, angry refund, kill switch (docs/demo-script.md) |
| 25-35 | The 12 questions below |
| 35-42 | Business case with their numbers (calculator below) |
| 42-45 | Next step: sandbox access, audio sample, owner for counsel review |

## 12 discovery questions
1. How many India customer contacts reach voice each month, and what share is about payments, changes, cancellations and property questions?
2. What does one human-handled voice contact cost you, fully loaded?
3. How many India bookings a month end in a failed or abandoned payment, and what happens to them today?
4. Which payment methods and failure reason codes appear in your booking events?
5. Who is the sender of record for outbound calls, and which caller-ID series has your category been allotted?
6. Do you already call customers about payments or arrivals, by people or by automation?
7. Which CCaaS platform handles your India queues, and does it expose a queue or transfer API?
8. Where should a confirmed special request land: booking system, property extranet or a case?
9. What are your India data-residency and sub-processor rules for a pilot vendor?
10. Who signs off on telecom and data-protection compliance, and how long does that take?
11. What result after eight weeks would make you continue, and what would make you stop?
12. Who besides you needs to say yes: payments, legal, security, procurement?

## Business-case calculator
Fill in with their numbers. Every output is an estimate until the pilot measures it against the holdout.

| Input | Symbol | Their value |
|---|---|---|
| Monthly India voice contacts that our two jobs could handle | C | |
| Fully loaded cost per human voice contact (Rs) | K | |
| Monthly India bookings with a failed or pending payment | F | |
| Containment: share of our calls resolved without a person | R | (pilot target 35-55%) |
| Recovery uplift: extra share of F that pays because of the call | U | (unknown; the holdout measures it) |
| Average booking value (Rs) | V | |
| Agoda's margin on a booking (%) | M | |

Monthly value and cost:
- Human contacts avoided = C x R
- Service cost avoided = C x R x K
- Extra paid bookings = F x U
- Margin recovered = F x U x V x M
- Our fee (option A) = USD 6,000 + Rs 25 x (C x R)
- Net monthly value = service cost avoided + margin recovered - our fee

Worked example with **hypothetical inputs, not Agoda data** (estimate, USD 1 = Rs 84 assumed): C = 20,000; K = Rs 120; R = 0.40; F = 10,000; U = 0.03; V = Rs 6,000; M = 15%.
- Contacts avoided = 8,000; service cost avoided = Rs 9,60,000
- Extra paid bookings = 300; margin recovered = Rs 2,70,000
- Fee = Rs 5,04,000 + Rs 2,00,000 = Rs 7,04,000
- Net monthly value = Rs 5,26,000 (estimate on hypothetical inputs)

## Objection handling
**"We'll build it ourselves."** You can, and you already build voice for suppliers (S-11). The parts that take time are not the model: they are the India telecom checks with a written decision before every dial, Hinglish read-back of amounts and dates, the holdout, and the tests that prove them. Those are built and tested here; the build-operate-transfer option means you can take it in-house after the pilot with the code, tests and runbooks, at a fixed fee. If you do build, the discovery answers and our test personas are yours to keep.

**"You're small."** True, and we will not pretend otherwise. We designed for that: you hold the kill switch from day one, the failure mode is "no call" rather than a bad call, half the pilot fee is at risk against your own holdout, and the system runs on your infrastructure if you want it to. The code is one typed service with its safety rules enforced by tests, so your engineers can read it in a day.

**"Security."** We hold no SOC 2 or ISO 27001 today and say so. What we have: no card data by design (out of PCI scope), India residency by default, row-level tenant isolation, audit logs, no training on your data, CERT-In and DPDP incident timers, and a 25-question answer sheet (docs/sales/security-pack.md). We will fund a third-party penetration test before go-live if you want one.

**"AI calls are risky with TRAI."** The rules require declared automated calls, consent, DND checks and complaint handling; they do not ban AI calls. Every one of those is a gate that runs before a single-use clearance is issued, and a complaint pauses the caller ID. Counsel signs off before the first live call.

**"Containment numbers look too good."** They are scripted-persona numbers on test data and we label them that way. We quote 35-55% as a pilot target and nothing higher until we have your audio.

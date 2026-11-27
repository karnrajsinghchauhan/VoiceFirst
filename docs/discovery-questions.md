# Discovery questions for Agoda

Every item tagged [CD] in the build brief. Each is built as config, never
hard-coded as truth. Config key in brackets where one exists.

## Company and product
1. Current rules for Agoda Homes, AgodaVIP and Agoda Cash that a service call may touch.
2. India payment methods offered (UPI, Paytm, netbanking, cards) and the payment-failure taxonomy (reason codes) we will receive in `booking_event`.
3. Model versions in production and the number of internal LLM tools (to avoid duplication).
4. Storage vendors in the private cloud (object store, KMS, Postgres operator).
5. Agoda-approved brand phrasing and brand-voice guide for Hindi, Hinglish and English. [`prompts/*`]

## Vendor standards (Booking Holdings)
6. Supplier code of conduct, security questionnaire, privacy addendum, responsible-AI principles.
7. Is Agoda notified, or expected to be notified, as a Significant Data Fiduciary? (REQ-DPDP-10)
8. Allowlist of provider regions for processing (REQ-DPDP-09). [`residency.allowed_regions`]

## Telecom (TRAI / DoT)
9. Which 1600xx/1601xx series applies to Agoda's sender category, and which OAP. [`cli_registry`, `compliance.service_series`]
10. Legal source of the 09:00-21:00 window under current regulations (we apply it as house policy). [`compliance.call_window`]
11. Counsel sign-off for J1 dialling a DND-flagged number on a transaction basis. [`compliance.dnd_j1_transaction_signoff_ref`]
12. Telecommunications Act 2023 section references for consent, DND and complaints (REQ-TEL-01).
13. CNAP and Truecaller business verification status for the declared CLIs (REQ-CLI-01).
14. SIP trunk choice (Tata or other) via LiveKit SIP. [`TELEPHONY`]

## Data protection
15. Retention period for consent records as the law requires (REQ-DPDP-07). [`retention.consent_days`]
16. Whether IT (Intermediary Guidelines) Amendment Rules 2026 SGI labelling applies to our calls (REQ-AI-01). We disclose regardless.
17. Indian counsel sign-off on docs/compliance.md before go-live.
18. Grievance officer contact and grievance channel URL to carry in every outcome (REQ-CP-03). [`grievance.*`]

## Payments
19. Agoda-hosted pay-link format and expiry (REQ-PAY-02). [`payment_link.*`]

## Voice and models
20. Licence for IndicConformer (self-hosted STT).
21. Licence for Indic Parler-TTS / IndicF5 (self-hosted TTS).
22. Agoda's own Hinglish audio for the WER/CER benchmark (11.8).

## Measurement
23. CSAT survey via WhatsApp utility template: is it allowed, and which template text. [`analytics.csat_template`]

## Other jurisdictions
24. Details of SG, TH, MY, US, EU policies before any non-+91 dialling (5.8).

## Cost model (carried from earlier research, re-confirm before quoting)
25. Plivo India Rs 0.38/min (30-s pulse); Vapi $0.05/min hosting; Retell $0.07-0.31; Bland $0.12-0.14; ElevenLabs Agents $0.08/min overage.

## Raised during the build
Resolved: item 26 (identity before booking details) was settled by D-017.
27. Male-voice Hindi/Hinglish lines: does Agoda want a male voice option? (Only female lines exist; boot rejects a male voice until they do.)
28. Agoda app deep link for customer-initiated add-on questions (D-001). [`wiring/backend.AGODA_APP_LINK`]
29. CCaaS platform and queue API for warm transfer (D-015).
30. Where confirmed details and special requests should land: booking system API, property extranet, or a human case (currently a CRM case).
31. The declared CLI per journey (D-014). [`compliance.cli_by_purpose`]
32. India BNPL: is the rule still "pay on or before the payment date with an India-issued instrument"? Could not be verified on 2026-11-27 (docs/sources.md); the engine never calls after `payment_due_at`.
33. Is "Book with Zero Pay" a current payment option, and how should the agent describe it?
34. What share of Indian bookings are under INR 5,000 a night? (The Travel Outlook figure could not be verified.)
35. Which Agoda-hosted payment-link format and expiry should the WhatsApp template carry? (REQ-PAY-02)

## Cars24
36. Which appointment types should the pilot cover: seller home inspections, buyer test drives at home, or both? Which cities?
37. How far ahead of a slot should the confirmation call go (default 18 hours), and how are reschedules handled today?
38. Which of these calls do your existing voice agents already make (S-36, S-38), so we add only what is missing?
39. Sender entity and declared caller-ID series for Cars24 service calls; WhatsApp opt-in source for buyers and sellers.
40. Which CRM or ticketing system receives notes and reschedule requests?
41. Which documents should the agent remind sellers and buyers to keep ready (we use RC, insurance, PUC and a driving licence)?
42. Is any pilot call connected to lending or payments? (Out of scope here; RBI recovery-agent rules would apply.)

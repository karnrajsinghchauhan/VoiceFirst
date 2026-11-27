# Prompt changelog

Any change to prompts, tool schemas, model ids or the normaliser triggers the eval gate (brief 10.9, 11.9).

## v2.1 (2026-11-28)
- The client's name is a placeholder `{client}` (tenant setting `client.name`, default Agoda) in every line, WhatsApp template and the DPDP notice, so one engine can call for Agoda and Cars24 (D-035). Wording is otherwise unchanged; `make eval` scorecard identical (guardrails 100%, containment 60.3%).

## v2 (2026-11-23)
- Identity first (brief v3 S1, D-101 resolved): the opening is disclosure plus "Kya main {first_name} ji se baat kar rahi hoon?". City, property, dates and amount are spoken only after the person confirms; a child, a third party or the wrong person hears none of them.
- New acts `opening`, `j1_purpose`, `j2_purpose` replace `j1_opening` and `j2_opening`.
- New act `introduce`: after identity is confirmed, "who is this?" gets an introduction plus the current question, never the identity question again. Before this, "haan, main hi hoon" said in reply to a repeated identity question was read as consent to the payment link (found by test_req_trai_05_agent).
- Eval assertion `no_booking_detail_before_identity` added; C-11, C-12, C-13 and C-19 must never hear a booking detail.

## v1 (2026-11-23)
- Initial lines for J1 and J2 in Hinglish, Hindi and English. J1/J2 openings verbatim from brief 10.2/10.3.
- Fixed situations from brief 10.7: refund/cancel, opt-out, wrong person, third party, card/OTP, "are you a bot", injection, filler.
- Female voice only; REQ-AI-02 lint rejects a male voice until male lines exist.

# Tabletop scripts: CERT-In and DPDP breach

Run quarterly. Facilitator reads each inject; the team answers with the actions and the clock times.

## Scenario A: leaked console token (CERT-In)
1. 10:00 IST: an ops token appears in a public paste. Who notices, and what is `detected_at`? (Answer: the time of first notice.)
2. Actions: revoke token in the secret store; engage kill switch if any dial was triggered by the actor; open `security` incident (6 h clock); pull `audit_log` for the actor.
3. 15:30 IST: is the CERT-In report on track for 16:00? Who submits through Agoda's point of contact [CD]?

## Scenario B: transcript bucket exposed (DPDP + CERT-In)
1. Day 0 09:00: a misconfigured backup exposes encrypted transcripts plus, by mistake, the data key.
2. Actions: open `data_breach` (72 h Board report and 6 h CERT-In open together); rotate `AV_DATA_KEY`; re-encrypt; list affected principals from `call_outcomes`.
3. Day 0 12:00: draft the principal notice in Hindi, Hinglish and English ("without delay").
4. Day 3 08:59: confirm the Board report has been sent and `reported_at` recorded.

## Scenario C: complaint spike
1. Two unique DLT complaints within 3 days. Expected: all campaigns pause automatically and a sev1 page fires. Who reviews before `lift_campaign_pause`?

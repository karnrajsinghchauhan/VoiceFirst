# /demo: five-minute talk track

For Karn. Open /demo, enter the passcode, keep this beside you. Everything on screen comes
from the engine; providers are mocks and the customer is a scripted persona, so say so once
at the start.

## 0:00 Set the frame (30 s)
"This is the real engine on test doubles: the same dispatcher, compliance gates and agent
that would run on Agoda's infrastructure. No real call or WhatsApp leaves this laptop."

## 0:30 Failed UPI payment (90 s)
Pick it and press Call. Point at the left column as it fills:
- the holdout check runs first and is never overridden;
- ten compliance gates, in order: +91 only, kill switch, consent, DND, opt-out lock, A2P
  declaration, number series, caller ID status, call window, attempt cap;
- one single-use clearance, the only thing the dialler accepts.
Then the right column: AI and recording disclosure first, identity before any booking
detail, consent before the link, amount read back in words. Finish on the WhatsApp utility
template (with the grievance line), QA 100, cost in paise.

## 2:00 Angry refund (45 s)
"Paise kat gaye." The agent does not argue or promise a refund: it logs a case and warm
transfers with a summary. "Disputes stay with humans, which is how your CS team already
works." Point at the CRM ticket.

## 2:45 Card number read out (30 s)
The customer reads a card number. The transcript never shows it, the call is flagged
sensitive, and the agent says it only sends links.

## 3:15 Child answers / stop calling me (30 s)
Child: nothing about the booking is said, the call ends. Stop calling: number marked DNC,
confirmed once, call ends; no consent request for 90 days.

## 3:45 Kill switch (45 s)
Start campaign; calls tick up. Press Kill switch. The campaign stops and shows the measured
time from the click to the first refused dial (target under 5 s). Queued calls are dropped.
Release it afterwards.

## 4:30 Close (30 s)
"What you saw is what runs in the pilot. Real voice is the same engine with keys plugged in;
the 10% holdout gives you lift you can audit."

If something fails on stage: switch to the recorded runs on the home page, which come from
the same code path (D-024).

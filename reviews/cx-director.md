# R1 review: Agoda CX director

Blind review, branch v3/pitch-pack, 2026-11-27. Read-only; `make demo` run once.

## Verdict

The safety story is real and better than most vendors show me. The AI cannot move money (ten allowlisted tools), disclosure comes first, the holdout is fixed before any gate runs, and the letter is mostly honest about what is mocked. I would not sign yet, because the human side of the loop is not finished. When the AI cannot finish a call it promises the customer a callback. That callback is written to a table nothing reads. In production there is no live transfer at all. The resolution time I would be judged on cannot be measured from Zendesk. The pricing also pays for links sent and opt-outs, not for recovered payments. Fix the Critical and High items below and I would take this to a discovery call with a signature in view.

## Critical

### C1. Promised callbacks go nowhere
- **Evidence:** `wiring/backend.py:106-119` (`schedule_callback`) and `handoff/transfer.py:91-104` write a `CallbackRow`. A repo-wide grep finds no code that reads the `callbacks` table: no dialler, no console view, no API route, no alert. The customer-requested path and the error path (`voice/agent.py:686-697`) call `schedule_callback`, which opens no CRM ticket. The customer still hears "hamari team aapko call karegi" (`prompts/v2/lines.yaml:124`). In dev and test, every handoff becomes a callback (`wiring/runtime.py:40-44`).
- **Why it matters:** Breaking a promise to an angry customer with a payment problem is worse than not calling them. This is the call that ends up on social media and goes to my VP.
- **Smallest fix:** Every `CallbackRow` opens a Zendesk ticket (reuse `crm/cases.open_case`) with `due_at` and priority. Add a `/callbacks` list to the console. Schedule an alert for any callback that is overdue and has not been acknowledged.

## High

### H1. No live human in production; the demo shows a transfer the pilot cannot do
- **Evidence:** A production boot raises `NotBuiltYetError("AV-CCAAS-1")` (`wiring/runtime.py:41-42`, D-015). The demo seeds one free agent per queue (`demo/engine.py:78`), and `demo-script.md` 2:00 says the agent "warm transfers with a summary". The one-pager's promise table states warm transfer as fact.
- **Why it matters:** "Humans in charge" is our public position. In the pilot as built, every dispute becomes a callback, and C1 means that callback is lost.
- **Smallest fix:** Label the demo transfer "simulated agent". In the one-pager and proposal, state that the pilot's handoff is a Zendesk ticket plus Agoda's callback queue until the CCaaS adapter ships. Make the CCaaS adapter a named week-2 exit criterion.

### H2. The product has never made a real phone call
- **Evidence:** STATUS.md shows 0/20 real calls and M8 blocked. Real telephony raises `NotBuiltYetError("AV-M8")` (`wiring/runtime.py:49-50`). Latency and WER come from a mock codec. Yet `demo-script.md` 4:30 says "Real voice is the same engine with keys plugged in".
- **Why it matters:** Hinglish recognition on a 3G line is the whole bet. I would be paying USD 10,000 at signature for something no phone has heard.
- **Smallest fix:** Delete that sentence. Make the 20 approved test calls, with measured p50/p95 and WER, a condition before the signature invoice, or move the first payment to the week-3 exit.

### H3. Case resolution time cannot be measured from Zendesk
- **Evidence:** `resolved_at` is set only by a manual console POST (`api/routes/records.py:246-256`). Zendesk ticket status is never read back. `analytics/metrics.resolution_time` has no loader in `queries.py`. `handoff/transfer.sla_breaches` is called only from tests.
- **Why it matters:** Resolution time and CSAT are the metrics I report. If they depend on agents clicking a second console, the numbers will be wrong or missing.
- **Smallest fix:** Add a Zendesk webhook (or poll) for `solved` that calls `transfer.resolve`, plus one query that feeds `resolution_time`. Run `sla_breaches` on a schedule that pages someone.

### H4. "AI-resolved contact" pays for links sent and opt-outs
- **Evidence:** Proposal section 3 defines it as `link_sent`, `details_confirmed` or `opted_out`. The code's `AI_RESOLVED` excludes `opted_out` (`analytics/metrics.py:20`). Neither definition requires the payment to complete.
- **Why it matters:** I would pay Rs 25 each time a customer says "stop calling me", and for every link nobody clicks. Finance will reject that. The proposal and the code also disagree.
- **Smallest fix:** Make J1 billable only when a `confirmed` event arrives within N hours of `link_sent`, count `details_confirmed` for J2, and drop `opted_out`. Use one definition in both proposal and code.

### H5. CRM writes are not idempotent and have no dead-letter queue
- **Evidence:** `providers/crm/zendesk.py:62-80` always POSTs a new ticket, with no upsert on `external_id`/`call_id`. In `wiring/backend.py:126-134`, if `open_case` fails after `queue.connect`, the transaction rolls back the `HandoffRow` while the human is already on the line. The call then drops into the callback path from C1. Brief S5 (upsert, DLQ, signed webhooks) is not built.
- **Why it matters:** A Zendesk outage would silently lose dispute cases. Retries would create duplicate tickets my agents have to merge.
- **Smallest fix:** Upsert by `external_id = call_id`. On CRM failure, keep the handoff row and enqueue the case to a DLQ table with an alert, instead of rolling back.

## Medium

- **Pilot timeline disagrees and has no power calculation.** The letter (section 10) says live traffic runs in weeks 5-8. The proposal (2.4) says live at week 4 with a read-out at week 7, which gives about 3 weeks of data at a 10% holdout. The at-risk half depends on a CI that may be underpowered. **Fix:** use one timeline, and add a sample-size estimate to the discovery questions.
- **Fit with our in-house voice agents is asserted, not designed.** "We are not proposing to replace that" (letter, line 76). Nothing covers our own outbound and opt-out lists, or contact-frequency caps across systems, so a customer could be called twice. **Fix:** add a discovery question, and a gate that reads Agoda's suppression or contact-history topic.
- **Callback time is fixed at 2 h and ignores the customer.** `CALLBACK_DELAY` is fixed, and the customer's "when" is only pasted into the reason (`backend.py:111-118`). It can also fall after `payment_due_at`. **Fix:** parse "when", and cap it before the payment deadline.
- **The weekly review (S4) is a promise, not a process.** There is no `docs/weekly-review/`, clustering or drift alert yet, but the letter promises a "weekly review of every failed or low-scoring call". **Fix:** say "manual weekly review" until S4 ships.
- **A grievance placeholder reaches customer output.** `make demo` prints "Agoda grievance officer: [CD: grievance contact]". **Fix:** refuse to boot outside dev while the value is still a placeholder.
- **The handoff SLA is the legal floor.** 48 h acknowledgement and 30-day resolution (`handoff/summary.py:15-16`) are E-Commerce Rules limits, not CX targets. **Fix:** make the SLAs per-queue config set by Agoda.

## Low

- **Identity check is thin.** One "haan ji" unlocks the city and the amount (demo transcript). Consider asking for a second factor, such as the booking month, before saying the amount.
- **Containment does not match the target.** Containment of 60.3% sits above the stated "pilot target 35-55%" (STATUS.md), with no explanation. Explain it, or drop the target.
- **Zendesk is the only CRM adapter** (`crm/factory.py`). That is fine for us; the docs should say "Zendesk only".

# Decisions

Format: ID, date, decision, why, what would change it.

## D-001 (2026-11-23) J2 carries no offers
- Decision: J2 (booking confirmation / pre-arrival) never carries promotional
  content. Connected-trip offers move to J7. If the customer asks about add-ons,
  the agent sends an Agoda app link with no persuasion and logs
  `customer_initiated_offer_request`.
- Why: service calls must not carry promotional content (TRAI TCCCPR), and the
  purpose of the call limits which data we may use (DPDP purpose limitation).
- Would change it: counsel confirming a lawful basis for in-call offers on a
  service CLI, which we do not expect.

## D-002 (2026-11-23) No git remote, no PRs this session
- Decision: work in a local git repo with one commit per milestone; no PRs.
- Why: the working directory was empty with no remote, and the GH_TOKEN in the
  container is invalid (`gh auth status` fails).
- Would change it: Karn supplies a repo and a valid token; then push `main`
  and open one PR per milestone from the milestone tags.

## D-003 (2026-11-23) Event bus test double in addition to Redpanda
- Decision: `core/bus.py` defines one `EventBus` interface with two
  implementations chosen by config at boot: `kafka` (aiokafka, speaks the Kafka
  API; Redpanda in compose, Agoda Kafka in prod) and `memory` (deterministic
  test double). Production config rejects `memory`.
- Why: same rule as providers (7.7): mocks are test doubles; production
  validator rejects them. Docker Hub returned 429 for Redpanda and LiveKit
  images this session, so tests cannot depend on a running broker.
- Would change it: nothing; this is the standard provider pattern.

## D-004 (2026-11-23) LiveKit pinned at 1.8.x, voice path not exercised
- Decision: pin `livekit-agents==1.8.13` (latest 1.8.x on PyPI 2026-11-23; 2.0.0b2 is beta) in `pyproject` optional
  extra `voice`. The text-mode agent (M3) is independent of LiveKit; the
  LiveKit worker adapter is a thin module that is only imported in the voice
  extra.
- Why: brief 7.2 says 1.8.x is stable, 2.0 beta. No provider keys exist and
  the LiveKit image could not be pulled, so M8 is "blocked: no keys".
- Would change it: keys in `.env` and a pullable `livekit-server` image.

## D-005 (2026-11-23) Single-process modular monolith with SQLAlchemy over Postgres; SQLite for unit tests
- Decision: Postgres 16 is the only production store. Unit and property tests
  run on SQLite in-memory through the same SQLAlchemy models; integration
  tests (`make e2e`) run on Postgres.
- Why: the Hypothesis state machine runs 10,000 examples per CI run; a fresh
  Postgres transaction per example is too slow for the gate budget. The
  single-use clearance consumption is a conditional UPDATE that behaves the
  same on both engines, and the e2e suite proves it on Postgres.
- Would change it: a behavioural difference found between the two engines on
  a tested path.

## D-006 (2026-11-23) Python 3.12 via uv
- Decision: the container has 3.13; uv installs and pins 3.12.13.
- Why: brief 7.1.
- Would change it: nothing.

## D-007 (2026-11-23) Synthetic caller is the scripted seeded mock
- Decision: all persona evals in this session use the deterministic scripted
  caller and the deterministic mock agent LLM policy.
- Why: no LLM keys. 11.2 allows a seeded scripted mock when two keys do not
  exist. Results therefore prove the guardrail and tool layer, not LLM
  behaviour; the report says so on its first line.
- Would change it: two LLM keys in `.env`; rerun `make eval` with
  `AV_CALLER_LLM` and `AV_LLM` set.

## D-008 (2026-11-23) J1 under DND requires recorded legal sign-off
- Decision: `compliance.dnd_j1_transaction_signoff_ref` is `null` by default,
  so any DND flag blocks J1 too until counsel's sign-off reference is
  configured.
- Why: REQ-TRAI-04. Failing closed is the only safe default.
- Would change it: counsel's written sign-off.

## D-009 (2026-11-23) The mock agent policy is the production policy's deterministic core
- Decision: guardrails (opt-out, handoff triggers, PAN/OTP redaction,
  dark-pattern filter, tool allowlist) run outside the LLM, before and after
  every turn. The LLM only proposes the next utterance and tool call; the
  guardrail layer can override it.
- Why: P1-P3 must hold even when the model misbehaves (C-16 injection).
- Would change it: nothing.

## D-201 (2026-11-23) One dispatcher writer per tenant; items processed one at a time
- Decision: `campaigns.Dispatcher.run_due` takes one due queue item per transaction and runs
  it to the end (gates, dial, call, outcome) before taking the next. Deploy one dispatcher
  replica per tenant.
- Why: the attempt-cap and cooldown gates count `dial_attempts` rows. With a single writer,
  no second clearance for the same event or number can be minted between a gate evaluation
  and its dial, so the counts are exact without a second check inside dial.
- Would change it: throughput needs beyond one sequential dispatcher. Then partition the
  queue by phone hash (one writer per partition) rather than adding locks.

## D-202 (2026-11-23) Lift is intention-to-treat over J1 queue items
- Decision: population = every booking that received a J1 queue item; arm = the holdout
  bucket function (not the holdout_members table); success = a later `confirmed` event.
- Why: bookings that pay before any gate runs are still counted in the right arm, so
  neither arm is biased by who happened to be reached.
- Would change it: Agoda supplying a different payment-success signal than `confirmed`.

## D-203 (2026-11-23) Journey timing defaults are config, not truth
- Decision: J1 for payment_pending waits 2 h after the event; no J1 after payment_due_at
  (BNPL can no longer be paid, so a call would contradict the rule); J2 is due 2 days before
  check-in at 11:00 IST. Time-based gate failures (window, cooldown) re-queue the item
  1 h later; other gate failures block it. All in `campaigns.journeys.JourneyRules` [CD].
- Why: the brief gives no thresholds.
- Would change it: Agoda's answer in discovery.

## D-204 (2026-11-23) A newer booking event supersedes queued calls for that booking
- Decision: ingesting any newer event for a booking drops its queued items
  (`superseded_by_newer_event`), then plans afresh. Redelivered event_ids are no-ops.
- Why: a paid, cancelled or changed booking must not get a stale call; Kafka delivers at
  least once.
- Would change it: nothing expected.

## D-011 (2026-11-23) Merge order D, E, F before B/C
- Decision: merge W-D, W-E and W-F as they finish; merge W-BC last, then wire.
- Why: W-BC (voice + tester) is the largest stream; the others touch disjoint
  files, so waiting would only delay `make check` on the integrated tree.
- Would change it: a file overlap between W-BC and an earlier merge.

## D-012 (2026-11-23) Helm chart not linted in this session
- Decision: ship the chart without `helm lint`/`helm template` output.
- Why: get.helm.sh is blocked by the session's network policy.
- Would change it: run `helm lint deploy/helm/agoda-voice` in CI (added to the
  next-tasks list).

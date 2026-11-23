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
## D-301 (2026-11-23) Data key for encryption at rest is postcall-owned
- Decision: `app/postcall/settings.py` reads `AV_DATA_KEY` (a Fernet key). Transcripts
  and audio references are redacted first, then encrypted. A fixed dev key exists for
  tests; `validate_postcall_for_production` rejects it.
- Why: one owner for the key; core config stays untouched by W-E.
- Would change it: Agoda's KMS (envelope encryption) once storage vendors are known [CD].

## D-302 (2026-11-23) Erasure pseudonymises outcomes and keeps consent and opt-out rows
- Decision: erasure deletes transcripts and audio, pseudonymises call outcomes
  (phone hash and booking id replaced), and keeps consent records and opt-outs.
- Why: outcomes feed the holdout lift measurement; consent records prove the lawful
  basis of past calls; opt-outs are what stops the number being called again.
- Would change it: counsel's view on consent-record retention [CD 15].

## D-303 (2026-11-23) Generic domain errors are HTTP 400; 422 stays request validation
- Decision: one exception handler maps typed errors to statuses (401/403/404/409/
  502/500, else 400). FastAPI's own 422 is the only request-validation response.
- Why: two error shapes must never share a status code in the OpenAPI document.
- Would change it: nothing.

## D-304 (2026-11-23) Rights-request SLAs default to 48 h ack and 30 days
- Decision: `AV_RIGHTS_ACK_HOURS=48`, `AV_RIGHTS_RESOLVE_DAYS=30` as house defaults.
- Why: statutory DPDP timelines for each right are [CD]; we pick the stricter house target.
- Would change it: counsel's confirmation of the statutory periods.
## D-010 (2026-11-23) A tenth agent tool, send_app_link
- Decision: the allowlist is the nine P1 tools plus `send_app_link`, which sends the Agoda
  app link by WhatsApp utility template only when the customer asks about add-ons, and logs
  `customer_initiated_offer_request`.
- Why: D-001 requires the agent to send an app link; none of the nine tools does that. The
  tool moves no money, carries no offer and no persuasion.
- Would change it: Agoda preferring a spoken pointer to the app with no message at all.

## D-101 (2026-11-23) The verbatim openings are spoken before identity is confirmed
- Decision: the J1/J2 openings from brief 10.2/10.3 are the first utterance, so they name the
  city (J1) or property and date (J2) before the callee confirms identity. Wrong person, third
  party and child then get nothing further.
- Why: the brief fixes the opening text and REQ-DPDP-01 needs purpose in the first utterance.
- Would change it: Agoda choosing a generic first line ("aapki Agoda booking ke baare mein")
  with the identity check before any booking detail [CD].

## D-102 (2026-11-23) Local turn detector, not the inference gateway
- Decision: the LiveKit worker uses livekit-plugins-turn-detector 1.8.13 MultilingualModel
  (local, deprecated in favour of inference.TurnDetector) with fixed endpointing 0.5/1.6 s,
  adaptive interruption at 0.2 s, and preemptive generation on.
- Why: inference.TurnDetector calls LiveKit Cloud (residency, P4) and has a `local_fallback`
  runtime fallback (rule 6.1).
- Would change it: a self-hosted inference endpoint inside India with fallback disabled.

## D-103 (2026-11-23) Low STT confidence: act on safety triggers, re-ask everything else
- Decision: below 0.9 confidence the agent acts only on opt-out, human, dispute, money,
  emergency, minor, card/OTP or machine signals; anything else (consent included) gets
  "awaaz saaf nahi aayi" and counts as a failed attempt.
- Why: audio evals on 3% loss showed a garbled opt-out read as consent and a link sent.
- Would change it: real STT confidence calibration from M8.

## D-104 (2026-11-23) Guardrail rate excludes task completion
- Decision: eval checks prefixed `task_` (expected outcome, required tools, no unneeded
  handoff) are reported as task success; guardrail rate counts only safety checks.
- Why: a safe handoff on a bad line is not a guardrail breach; mixing them hid the real
  safety number.
- Would change it: nothing.

## D-105 (2026-11-23) Mock latency and audio timing are a model
- Decision: mock providers advance a simulated clock by seeded latencies (STT 0.12 s, LLM
  0.35 s, TTS first audio 0.12 s medians); end-of-speech to first audio, barge-in and false
  cutoff come from a timing model of the pinned turn handling. Reports label them simulated.
- Why: no keys and no LiveKit image (M8 blocked); 11.8 targets still need a number to gate on.
- Would change it: M8 measurements on real audio.

## D-013 (2026-11-23) import-linter forbids only direct imports of telephony.dial
- Decision: `allow_indirect_imports = true` on the dial contract; the AST test in
  test_static_proofs still pins every direct import to campaigns/dispatcher.py.
- Why: the composition root (app/wiring) must build the Dispatcher, which imports
  dial. The brief's rule is about who can call dial, which only a direct import allows.
- Would change it: nothing short of moving composition out of the app package.

## D-014 (2026-11-23) The CLI per journey is configuration
- Decision: `compliance.cli_by_purpose` in Settings ([CD] placeholders); the seed
  data, the dispatcher wiring and the demo all read it.
- Why: the wiring test found two modules holding different CLI numbers (rule 6.5).
- Would change it: DLT registration supplies the real CLIs.

## D-015 (2026-11-23) No CCaaS human queue in this build
- Decision: dev/test use InMemoryHumanQueue with nobody available, so every
  handoff books a callback and says so (P2). Production boot raises
  NotBuiltYetError("AV-CCAAS-1").
- Why: Agoda's live-agent platform and queue API are unknown [CD].
- Would change it: Agoda names the CCaaS platform and grants a sandbox.

## D-016 (2026-11-23) Mock telephony carries a scripted cooperative caller
- Decision: when telephony is `mock`, the dispatcher's CallRunner listens to the
  C-01 scripted caller; any real telephony provider raises NotBuiltYetError("AV-M8")
  at boot until the LiveKit media path is bridged.
- Why: one path per configuration; no silent half-real calls.
- Would change it: provider keys and the M8 media bridge.

## D-017 (2026-11-23) Identity first; D-101 resolved
- Decision: prompts v2 open with the AI and recording disclosure plus "Kya main {first_name} ji se baat kar rahi hoon?". City, property, dates and amount come only after a confirmed yes (`j1_purpose`/`j2_purpose`).
- Why: brief v3 S1; a child, spouse, front desk or wrong number must learn nothing about the booking.
- Would change it: nothing; Agoda may only tighten it (e.g. ask for the booking's last 4 characters).

## D-018 (2026-11-23) "Who is this?" after identity gets an introduction, not the identity question
- Decision: after identity is confirmed, a clarifying "kaun?" gets the `introduce` line plus the current question.
- Why: test_req_trai_05_agent found that a repeated identity question let "haan, main hi hoon" count as consent to the payment link (brief 10.6 requires consent to the ask itself).
- Would change it: nothing.

## D-019 (2026-11-23) False-interruption metric uses the agent's own backchannel rule
- Decision: the audio simulator classifies a barge-in with `guardrails.classify(..., overlap=True)`, the rule the agent acts on, instead of the lexicon alone.
- Why: the metric reported a false interruption the agent would not have made ("hmm achha" misheard as "ha" on 3G); a measurement must measure the behaviour.
- Would change it: real LiveKit traces in M8 replacing the timing model.

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

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

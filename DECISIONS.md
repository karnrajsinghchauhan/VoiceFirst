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

## D-020 (2026-11-23) Tenant isolation by Postgres row-level security; one tenant per runtime
- Decision: every table carries tenant_id; phone-keyed tables are keyed (tenant_id, phone_hash). Migration b2c3d4e5f6a7 enables and forces RLS with policy `tenant_id = current_setting('app.tenant_id')`. `make_engine(url, tenant_id)` declares the tenant on every connection; a runtime serves one tenant. Production refuses to boot when the DB role is a superuser (superusers bypass RLS).
- Why: brief v3 S7; isolation must hold even when a query forgets its tenant filter. One runtime per tenant also matches build-operate-transfer (each client runs its own).
- Would change it: a shared multi-tenant runtime, which would set app.tenant_id per transaction from the authenticated principal.

## D-021 (2026-11-23) One bearer path, three credential kinds; production is keys and SSO only
- Decision: `get_principal` resolves `avk_` API keys (sha256 of a 32-byte secret at rest, scoped, rotatable, last-used), OIDC ID tokens (RS256 against the issuer JWKS; group claim to role, most privileged wins), or static dev tokens. Production refuses any static token. A Principal carries its effective permissions (role narrowed by scopes); scopes beyond the role are refused at issue.
- Why: brief v3 S7 (SSO, scoped keys, RBAC); one authorisation check (`authorize`) whatever the credential.
- Would change it: SAML via the same group-to-role table when a client requires it.

## D-022 (2026-11-27) /demo runs the real engine on an isolated in-memory store per call
- Decision: `POST /demo/run` builds a fresh SQLite engine, memory bus and frozen clock (11:00 IST today) per call, seeds one CLI and consent row, ingests one booking event and runs the real dispatcher: holdout, every gate, single-use clearance, dial, agent, tools, post-call. The timeline is read from what the engine published. The demo kill switch engages `compliance.killswitch` on the dispatcher and times the first refused dial. Endpoints need `x-demo-passcode` (`AV_DEMO_PASSCODE`); without it they return 404.
- Why: brief v3 S10 says the demo uses the real engine, and a demo must never touch tenant data or the shared kill switch.
- Would change it: a hosted demo that should show a real tenant's console; then it runs as its own tenant.

## D-023 (2026-11-27) The demo's human queue has one free human per queue
- Decision: the demo engine models a staffed queue, so a dispute ends in a real warm transfer with its summary (`handed_off`). Dev and production keep D-015.
- Why: the eval persona C-05 expects a handoff; with nobody free the agent correctly books a callback, which hides the warm-transfer path the demo is meant to show.
- Would change it: Agoda's CCaaS sandbox (AV-CCAAS-1).

## D-024 (2026-11-27) One code path for live and recorded demo runs; paced display only in the browser
- Decision: `web/scripts/record_demo.py` now records by calling `DemoService`, replacing its own copy of the pipeline. Gate labels live in `app/demo/timeline.py`. Engine times are real milliseconds; `web/src/lib/playback.ts` spaces items out for reading without changing order or content. The angry-refund scenario uses persona C-05 ("angry, paise kat gaye").
- Why: rule 6.5 (no shadow copies); a mock call finishes in milliseconds, which nobody can read.
- Would change it: real provider latency (M8), when the timeline can play at real speed.

## D-025 (2026-11-27) `app/wiring/runtime.py` owns the runtime builders
- Decision: `Runtime`, `build_runtime` and `build_dispatcher` moved from `wiring/main.py` to `wiring/runtime.py`; `main.py` keeps the API composition and re-exports the old names. `build_dispatcher` takes an optional caller and result hook.
- Why: the demo service needs the dispatcher and the API needs the demo service; one module holding both was an import cycle.
- Would change it: nothing.

## D-026 (2026-11-27) CI runs locally until GitHub Actions runs on this repo
- Decision: `make check`, `make e2e` and `npx playwright test -c playwright.demo.config.ts` run locally before each push, and their results go in the PR description.
- Why: the repo's Actions page reports "GitHub Actions is not currently enabled on this repository" although the setting allows all actions; no run has ever been created.
- Would change it: GitHub support re-enabling Actions; then `ci.yml` is the gate again.

## D-027 (2026-11-27) docs/sources.md rows carry the URL they were checked against; unverifiable facts become [CD]
- Decision: every [V] row now links its source and states the check date. Five claims could not be confirmed and moved to [CD] and discovery questions 32-35: "Book with Zero Pay", the India BNPL instrument rule, "47% at INR 5,000 or less", the 18 Sep 2026 notification day (now "September 2026") and the G.S.R. number of the E-Commerce amendment. Two sources were corrected (Airbnb: Customer Experience Dive, not Storyboard18; MakeMyTrip: Deccan Herald, not The Hans India). Kafka volume is now dated (1.8 trillion in 2023; over 3 trillion in 2025).
- Why: NEXT.md section 3 and Karn's final-run instruction: verify in the browser, drop what cannot be verified.
- Would change it: Agoda confirming a [CD] item in discovery.

## D-028 (2026-11-27) The /agoda letter is generated from the repo's own facts
- Decision: `/agoda` (private, noindex, passcode) cites only `docs/sources.md` rows, `content/measured.json` results and labelled estimates; its call transcript is the recorded demo run and its question list is generated from `docs/discovery-questions.md`. `npm run pdf:agoda` prints it from the production build to `reports/agoda-letter.pdf`, which is committed (the only exception to the `reports/` ignore).
- Why: a letter that copies facts by hand drifts from the code and the sources.
- Would change it: nothing.

## D-029 (2026-11-27) The pitch pack lives on its own branch and PR
- Decision: `docs/sales/` (Markdown plus PDFs from `scripts/sales_pdf.py`), the launch-cost list, the MCP scaffold and the review fixes go on `v3/pitch-pack`, based on `v3/w3-frontend`, with its own PR. Site polish stays on PR #14.
- Why: PR #14 is the front end; sales documents and a server module would make it unreviewable on a phone.
- Would change it: Karn preferring one PR.
## D-030 (2026-11-27) The claims rule is a browser test over every public page
- Decision: `Src`, `Measured`, `Spec` and `Est` render `data-claim`; `web/tests/public-pages.spec.ts` walks the text of each public page and fails on any percentage or money amount outside such a mark, and runs axe for WCAG 2.1 AA. `GET /status` on the engine reports live checks (API, database, dialling state, provider mode) with no data, and an empty uptime history until one is measured.
- Why: brief v3 section 6 ("every public number needs a source or the label estimate") is only true if a test enforces it.
- Would change it: a public page that needs a numeric example; it then uses `Est`.

## D-031 (2026-11-27) MCP is a tool layer over existing services; the kill switch and consent are never tools
- Decision: `app/mcp` exposes six tools (list, pause and start campaigns; read outcomes; read the QA scorecard), each bound to one RBAC permission, reachable only with a scoped API key, and audit-logged whether allowed or refused. Kill switch, consent, DNC, payment links and any money action are on a refusal list, and no tool may require `killswitch:write`, `consent:write` or `apikeys:write`. JSON-RPC handler only; no transport, not deployed.
- Why: Karn's step 6; an agent may reduce calling (pause) but must not release the control that exists to stop it.
- Would change it: Agoda asking for agents to engage (never release) the kill switch; that would be a separate, audited tool behind its own scope.

## D-032 (2026-11-27) Section 5 review fixes
- Decision: fixed in code: callbacks open a CRM ticket; the handoff commits before the CRM call and a CRM failure pages a person; erasure and the nightly purge scrub booking-event payloads, clearances and handoff summaries; overdue CERT-In/DPDP reports page a person every 15 minutes (CronJob) and `POST /incidents/{id}/reported|acknowledge` stop the clocks; production refuses placeholder grievance, notice and payment-link values and refuses `stt=sarvam` until its confidence is calibrated; the Helm chart's `envFrom` placement (it now passes `helm lint`, closing D-012). Corrected claims: the demo's staffed queue is modelled, 0 real calls, the latency figure is modelled, Kubernetes effort excludes missing chart pieces, ICT-log retention is a deployment requirement, the billing unit is a paid J1 booking or a confirmed J2.
- Why: brief v3 section 5: fix every High and Critical with the smallest change; where a fix needs keys or a design, stop claiming it and queue it (PLAN.md).
- Would change it: nothing.

## D-033 (2026-11-27) Dialled calls run concurrently; gates stay single-writer (amends D-201)
- Decision: `run_due` clears and dials up to `call_workers` items sequentially, then runs those calls in parallel threads and records their outcomes; it never dials more calls than it can run. Default 1 (tests), Helm 20.
- Why: review R3 C1: one call at a time per tenant cannot serve a pilot. Clearance and the dial-attempt row commit before a call runs, so caps and cooldowns still count exactly (tested with a shared number).
- Would change it: moving the call loop into the LiveKit worker (PLAN item 1), after which the dispatcher only dials.

## D-034 (2026-11-28) Brand is BookedMeetings; the voice product is its /voice subsection
- Decision: `BRAND_NAME` defaults to BookedMeetings and the site URL to bookedmeetings.com (Karn, 2026-11-28; supersedes D-701's ownermeetings.com). `/` is the brand home; the voice product's pages live under `/voice` (home, product, security, pricing, changelog) with permanent redirects from the old paths. Status, company, legal and docs stay at the root because they cover the whole brand. The footer disclaimer names Agoda and Cars24. The domain is not bought (spending gate).
- Why: Karn wants one brand serving more than one client (Agoda, Cars24), with voice as one section of it.
- Would change it: Karn choosing a subdomain instead of a path.

## D-035 (2026-11-28) The client is tenant configuration, not text
- Decision: `Settings.client.name` (default "Agoda") fills `{client}` in every spoken line, WhatsApp template and notice. A tenant runtime serves one client (D-020), so Cars24 is a second tenant with `AV_CLIENT__NAME=Cars24`.
- Why: Karn wants to work with Cars24 as well; the engine must not say "Agoda" on a Cars24 call.
- Would change it: nothing.

## D-036 (2026-11-28) Cars24 is J2 with an appointment instead of a stay
- Decision: `booking_event` gains an optional `appointment` (kind home_inspection or test_drive, slot start, locality only) and `property`/`stay` become optional; `journeys.booking_shape` is the one owner of which shape an event has and ingest refuses both or neither (`EventShapeError`). The J2 flow and every guardrail are shared; only the lines differ (`j2a_*`), chosen in one place in the agent. Appointment calls go out 18 hours before the slot [CD]. A Cars24 tenant sets `client.name=Cars24`. Lending, EMI and collections calls are out of scope: they fall under RBI's fair-practice and recovery-agent rules, which this build does not implement.
- Why: Karn wants Cars24 call flows. A confirmation call has the same consent basis, number series and gates as J2, so a new purpose would duplicate compliance code for no gain.
- Would change it: a Cars24 journey with a different lawful basis (for example a promotional or lending call), which would need its own purpose and gates.

## D-037 (2026-11-28) Cars24 in the demo and a private /cars24 note
- Decision: `/demo` gains two Cars24 scenarios (home inspection confirmed; test drive needs a new time) that run as a Cars24 tenant, so the agent says Cars24. `/cars24` is a private, noindex note (passcode) citing S-35 to S-40: it credits Cars24's existing voice agents, proposes only appointment confirmations, states that no lending or collection calls are made, and leaves commercial terms to agree. Cars24 discovery questions are 36-42. Rate limits per bucket can be overridden by `AV_RATE_LIMIT_<BUCKET>` (the test server raises demo and gate; production keeps 30 and 10).
- Why: Karn wants to work with Cars24; Cars24 already runs voice AI at scale (S-36 to S-38), so the honest offer is a narrow, auditable addition.
- Would change it: Cars24's answers to the discovery questions.

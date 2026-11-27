# R3: staff voice-AI engineer review (branch v3/pitch-pack, 2026-11-27)

**Verdict.** The gating and guardrail engine is careful and well tested (113 voice and chaos tests pass; `make demo` runs). Nothing about real-time voice is proven yet. There is no live media path, and latency, barge-in and WER come from constants and an FSK text codec, not from speech. The dispatcher runs one call at a time per tenant, so 200 concurrent calls is not possible as built, and the Helm chart would not install. The docs mostly admit this. The pitch overstates two points: modelled latency is tagged "measured", and the Kubernetes move is quoted at "about 5 days".

## Critical

**C1. The dispatcher puts a hard limit of 1 concurrent call on each tenant.**
Evidence: `server/app/campaigns/dispatcher.py:168-175,213` (`run_due` calls `_dispatch`, which blocks on `self._runner.run(...)` until the call ends); `server/app/wiring/run_dispatcher.py:19-23`; `deploy/helm/agoda-voice/values.yaml:56` (`replicas: 1`); D-201. `make load` skips the dispatcher (`simulator/load.py:40` calls `run_text` in threads), so its "200 concurrent" result says nothing about dispatch.
Impact: at about 2 minutes per call, one tenant gets about 30 calls an hour. A pilot would never get above one live call.
Fix: make the dispatcher stop at dial. The clearance, `dial_attempts` row and `in_call` already commit in `_clear_and_dial`, so the single writer stays exact without waiting for the call. Hand the handle to a LiveKit agent dispatch and return; the worker records the outcome in its own transaction. Add a per-tenant `in_call` count gate to cap concurrency.

**C2. No live voice path exists, and the call loop lives in the wrong process.**
Evidence: `server/app/voice/livekit_worker.py:73-80` (`entrypoint` raises `NotBuiltYetError`); `server/app/wiring/runtime.py:49-50`; `server/app/providers/registry.py:102-105`. The conversation runs inside the dispatcher through `listener_factory`, not in the LiveKit worker. Disclosed as M8.
Impact: no pilot call can be placed, and M8 is a redesign (the loop must move into the LiveKit session), not a key swap.
Fix: run `run_conversation` inside `entrypoint`. Implement `Listener` over `AgentSession` events. Prove one outbound SIP call end to end on mock providers first.

## High

**H1. Modelled latency is shown as "measured", and the model leaves out the network.**
Evidence: `web/src/components/claims.tsx:71-74` puts a "measured" superscript on `latency` (`web/src/content/measured.json:45-50`, which itself says "modelled"), on `/agoda`. `server/app/simulator/audio.py:92` computes `max(endpoint, stt+llm) + tts_first`. It ignores `line_delay_ms` (150-400 ms one way, `line.py:134`), which is computed but never added. Barge-in "260 ms" is the constant `0.2+0.02+0.04` (`audio.py:112`). The medians are the constants in `registry.py:33`. So the gate at `evaluate.py:238` cannot fail.
Impact: a buyer reads 725/950 ms as observed; on PSTN, perceived latency is 300-800 ms higher even before real providers.
Fix: add a `modelled` variant to `Measured` and use it for latency and barge-in. Add 2x `line_delay_ms` to the model. Mark the gate non-gating until M8.

**H2. Batch, synchronous provider interfaces will miss the 800/1,500 ms target.**
Evidence: `server/app/providers/base.py:26,35,69` (whole-utterance `transcribe`, whole-text `synthesize`, full `next_turn`); `stt/sarvam.py:49-56` (blocking `httpx.post`, WAV upload, 3 s timeout); `voice/agent.py:252-255` (full LLM reply, then verify, then TTS). LiveKit preemptive generation (`livekit_worker.py:56`) never reaches these providers.
Impact: a realistic budget is 0.5 s endpointing + 0.3-0.6 s batch STT + 0.6-1.5 s full completion + 0.3-0.8 s full synthesis + PSTN, which gives a p50 of about 2-3 s. Blocking I/O would also stall the event loop.
Fix: the mock LLM only renders the acts the state machine chose (`providers/llm/mock.py:36-39`). So make deterministic template rendering the production path for scripted acts and take the LLM out of the hot path. Stream TTS per sentence and use streaming STT through async LiveKit plugins.

**H3. Any small deviation by a real LLM, or a slow turn, ends the call.**
Evidence: `voice/agent.py:288-289` (proposed tools must exactly equal the required tools); `291-300` (utterance checks raise); `671-673` (any `AgodaVoiceError` goes to the error path and hangs up); `llm/openai.py:25` (3 s timeout). The mock LLM matches by construction, so the "guardrails 100%" result tests nothing about a real model.
Impact: real models paraphrase and reorder tool arguments. Expect a high rate of `error` outcomes and callbacks in the pilot.
Fix: same as H2 (render scripted acts without the LLM). Or regenerate once from the same provider (not a fallback) and report the deviation rate against a real model.

**H4. The low-confidence safety rule (D-103) is dead in production.**
Evidence: `providers/stt/sarvam.py:66` hard-codes `confidence=1.0`. The audio evals that motivated D-103 got their confidence from codec erasures (`stt/mock.py:29-33`).
Impact: on a bad line, a garbled opt-out can again be read as consent and a payment link sent. That is the exact failure D-103 was written to stop.
Fix: map Sarvam's confidence if the API returns one. If it does not, return `confidence=None` and treat None as below the threshold for consent. Add a contract test that fails on a constant confidence.

**H5. The Helm chart cannot install, and "about 5 days" on Kubernetes is understated.**
Evidence: `deploy/helm/agoda-voice/templates/_helpers.tpl:37-39` renders `envFrom:` inside the `env:` list. I reproduced the render with PyYAML and it fails with "expected <block end>". `templates/deployment-voice-worker.yaml:28` runs `python -m app.voice.livekit_worker start`, but the module has no `__main__`/`cli.run_app`. `values.yaml:15-16` selects `plivo`/`meta_cloud_api`, which fail at boot. No livekit-server, livekit-sip, Redis or RTP port plan. The worker and dispatcher have no probes, PDB or `terminationGracePeriodSeconds`, so a rollout cuts live calls after 30 s. The `/agoda` page says "about 5 days" (`web/src/app/agoda/page.tsx:308-311`).
Impact: the transfer claim is not true today. The SIP media plane on Agoda's Kubernetes (UDP ranges, TURN, SBC allow-listing) is the hard part, and it takes weeks.
Fix: split `envFrom` into its own helper at container level. Add `if __name__ == "__main__": cli.run_app(server)`. Run `helm template | kubeconform` in `make check`. Reword the estimate: "after M8; LiveKit media plane not yet in chart".

## Medium

**M1. Observability stops at HTTP.** OpenTelemetry is declared (`server/pyproject.toml:17-18`) but never imported. Prometheus has only `av_http_requests_total` and the kill-switch gauge (`api/deps.py:41-46`). The voice package logs nothing. `CallOutcome.latency_ms` times LLM plus tools (`agent.py:235,264`), not end of speech to first audio, so the console and the gate show different metrics. `trace_id` does flow through records. Fix: per-stage latency histograms with `trace_id` exemplars and a live-calls gauge.

**M2. The transcript ignores barge-in.** `_emit` stores the full agent line as spoken (`agent.py:269,277-281`), even if the caller cut it off. Read-back checks assume full playout. Fix: record the interrupted flag from the LiveKit speech handle and count an interrupted read-back as not delivered.

**M3. The apology on the TTS-failure path is never heard.** `_error_path` emits apology text (`agent.py:692`) through the TTS that failed; the chaos test checks only the outcome (`test_voice_chaos.py:93-95`). Fix: a pre-rendered apology clip.

**M4. Kafka publishes block the dial transaction.** `bus.py:64` calls `flush(10.0)` per message inside DB transactions. Fix: a transactional outbox.

**M5. Cost per call is partly made up.** `llm=0` is hard-coded and duration comes from character counts (`agent.py:704-706,762`). Fix: token usage and CDR duration.

## Low

**L1.** Any overlap of 2 words or fewer is a backchannel (`guardrails.py:392`), so "ruko" or "ek minute" resumes the agent. Add hold words as their own class.
**L2.** `docker-compose.yml:36-38` has no `livekit/sip` service, so SIP cannot be tried locally.

## Proven vs modelled
Proven: gate order, single-use clearance under Postgres concurrency, kill switch under 5 s, guardrails against a scripted LLM, orchestration CPU. Modelled or absent: latency, barge-in, false cutoff, WER, STT confidence, real-LLM compliance, more than 1 call per tenant, Kubernetes install.

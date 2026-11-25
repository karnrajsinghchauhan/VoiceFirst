# Sizing (M10)

## What was measured (2026-11-23, `make load`)
200 concurrent mock sessions, mock providers, text mode:
- orchestration CPU: 3.6 ms per session (whole call), 44 MB peak RSS for the process;
- guardrail pass rate under load: 100%.

This is only the cost of our own orchestration (gates, guardrails, normaliser,
tool calls). It excludes STT, TTS and LLM inference, the LiveKit media path and
codec work, which dominate a real call. Real-provider sizing is blocked on keys
(M8) and must be redone before any capacity commitment.

## Planning numbers until M8 (estimates, not measurements)
| Component | Per concurrent call | Basis |
|-----------|---------------------|-------|
| Agent orchestration | < 0.01 vCPU | measured above |
| LiveKit agent worker (VAD, turn detector, audio frames) | ~0.25-0.5 vCPU, ~150 MB | estimate; LiveKit worker guidance [CD: confirm on pinned 1.8.13] |
| Hosted STT/TTS/LLM | network only | provider-side |
| Self-hosted STT/TTS (IndicConformer, Indic Parler-TTS) | GPU-bound | estimate; licence [CD] |

`values.yaml` sets `voiceWorker.sessionsPerPod: 20` on 2-4 vCPU pods,
consistent with the upper end of the estimate. Re-derive it from an M8 load
test with `make load` against real providers (cap: 20 real sessions, brief 11.10).

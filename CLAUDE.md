# Agoda Voice: engineering notes for agents and humans

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.

## Rules (from the build brief, section 6)
- One correct path. No fallbacks, no retry-with-another-provider.
- Exactly one provider per role, chosen by config at boot; bad config fails at startup.
- Typed errors derived from `AgodaVoiceError` (`server/app/core/errors.py`). Never return None for failure.
- Each fact has one owner module. Each function does one thing.
- pydantic v2 + mypy --strict. Validate only at edges (HTTP, Kafka, provider responses, config).
- Comments say why, not what. No emoji.
- `make check` before every commit.

## Where things live
- `contracts/schemas/*.json` is the single source of truth for records. Run `make gen` after editing; `make check` fails on drift.
- `server/app/compliance/` is the only package that can construct a `GateClearance`.
- `server/app/telephony/dial.py::dial` is the only function that places a call, and only `campaigns/dispatcher.py` may import it (import-linter).
- `server/app/voice/` holds the text-mode agent, prompts (versioned), guardrails, normaliser, tools.
- `server/app/simulator/` + `evals/` hold the tester.

## Commands
`make up | check | test | e2e | eval | eval-audio | load | chaos | seed | demo | report`

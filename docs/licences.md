# Licences for models and voices (REQ-AI-02, M10)

Rule: never clone a real person's voice; only stock voices licensed for
commercial telephony. Never OmniVoice default weights.

| Component | Role | Licence | Commercial telephony use | Status |
|-----------|------|---------|--------------------------|--------|
| Mock codec voice (`mock-female-1`) | TTS test double | Repo code | n/a (tests only) | In use |
| Sarvam Bulbul v3 stock voices | TTS | Sarvam commercial terms [CD] | [CD: confirm in writing] | Not contracted |
| ElevenLabs stock voices | TTS | ElevenLabs terms [CD] | [CD] | Not built |
| Indic Parler-TTS | TTS self-hosted | [CD] | [CD] | Not built |
| IndicF5 | TTS self-hosted | [CD] | [CD] | Not built |
| Sarvam STT | STT | Sarvam commercial terms [CD] | n/a | Not contracted |
| IndicConformer | STT self-hosted | [CD] | n/a | Not built |
| LiveKit Agents 1.8.13 | Voice runtime | Apache-2.0 | Yes | Pinned |
| LiveKit turn detector | Turn detection | LiveKit model licence [CD: verify for self-hosted commercial use] | [CD] | Pinned with livekit-agents |
| Noise set for line simulator | Evals | Generated in-repo (CC0 equivalent) | n/a | In use |

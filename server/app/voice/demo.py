"""`make demo`: one full J1 mock conversation (persona C-01, Hinglish), printed with its outcome."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.simulator.caller import PERSONA_DIR, load_persona
from app.simulator.scenario import run_text

DISCLAIMER = "Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda."


def render_demo(persona_id: str = "C-01", language: str = "hinglish", seed: int = 0) -> str:
    settings = Settings(environment="test", database_url="sqlite://")
    persona = load_persona(Path(PERSONA_DIR) / f"{persona_id}.yaml")
    run = run_text(settings, persona, language, seed)  # type: ignore[arg-type]
    out = run.result.outcome
    lines = [DISCLAIMER, f"Demo: {persona.id} {persona.title} ({language}), mock providers", ""]
    for turn in run.result.transcript:
        who = "AGENT   " if turn.speaker == "agent" else "CUSTOMER"
        lines.append(f"{who} {turn.text}")
    lines += [
        "",
        f"outcome: {out.outcome}",
        f"tools: {', '.join(t.name for t in out.tools_called)}",
        f"latency p50/p95 (simulated): {out.latency_ms.p50}/{out.latency_ms.p95} ms",
        f"cost (paise): {out.cost.model_dump()}",
        f"grievance: {out.grievance_channel}",
        f"provenance: {out.provenance_hash}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_demo())

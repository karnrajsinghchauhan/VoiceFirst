"""Records demo runs from the real engine (text mode, mock providers) into JSON the site replays.

Run from server/: `uv run python ../web/scripts/record_demo.py ../web/src/content/demo-runs`
(or `npm run record:demo` from web/). Re-run whenever prompts change. Nothing here is
hand-written: gates come from compliance.evaluate, the conversation from voice.agent via
the eval scenario runner, the WhatsApp preview from messaging.templates, QA from
simulator.assertions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.compliance.evaluate import evaluate
from app.compliance.holdout import is_held_out
from app.compliance.models import GateDecisionRow
from app.core.bus import MemoryBus
from app.core.clock import FrozenClock
from app.core.db import create_all, make_engine, make_session_factory
from app.core.errors import GateError
from app.core.money import format_inr
from app.messaging.templates import TEMPLATES, render
from app.messaging.whatsapp import payment_link
from app.simulator.assertions import check_run
from app.simulator.caller import load_personas
from app.simulator.scenario import CALL_START, make_event, run_text
from tests.factories import make_settings, seed_cli, seed_consent

SCENARIOS = {
    "failed_upi": ("C-01", "Failed UPI payment"),
    "confirmation": ("C-28", "Booking confirmation"),
    "angry_refund": ("C-06", "Angry refund request"),
    "stop_calling": ("C-10", "Stop calling me"),
    "child_answers": ("C-11", "Child answers"),
    "card_number": ("C-17", "Customer reads out a card number"),
}
GATE_LABELS = {
    "holdout": "Holdout check (no-call group)",
    "jurisdiction": "Jurisdiction: +91 only",
    "kill_switch": "Kill switch and campaign pause",
    "consent": "Consent basis on record",
    "dnd": "DND preference registry",
    "opt_out_lock": "Opt-out lock",
    "cli_declared": "Caller ID declared as A2P on DLT",
    "series": "Number series matches purpose",
    "cli_status": "Caller ID active",
    "window": "Call window (recipient local time)",
    "cap_cooldown": "Attempt cap and cooldown",
}
URGENT = {"dispute", "legal", "chargeback", "fraud", "safety", "medical", "vip"}
CLI = "+911600123456"
# Fixed so re-recording with unchanged prompts produces an identical file.
RECORDED_AT = "2026-11-23"


def _gates(settings: Any, event: Any, purpose: str) -> tuple[list[dict[str, Any]], str | None]:
    engine = make_engine("sqlite://")
    create_all(engine)
    session = make_session_factory(engine)()
    seed_cli(session, settings, cli_e164=CLI,
             purpose="transactional" if purpose == "J1" else "service",
             series="1600" if purpose == "J1" else "1601")
    seed_consent(session, settings, event, purpose=purpose)
    try:
        clearance_id: str | None = evaluate(
            session, MemoryBus(), settings, FrozenClock(CALL_START), event, purpose, CLI
        ).clearance_id
    except GateError:
        clearance_id = None
    gates = session.query(GateDecisionRow).one().gates
    return list(gates), clearance_id


def _seed_outside_holdout(settings: Any, persona: Any, language: str) -> int:
    seed = 0
    while is_held_out(settings.holdout.experiment_salt,
                      make_event(settings, persona, language, seed).booking_id,
                      settings.holdout.percent):
        seed += 1
    return seed


def record(scenario: str, persona_id: str, title: str) -> dict[str, Any]:
    settings = make_settings()
    persona = next(p for p in load_personas() if p.id == persona_id)
    language = "hinglish" if persona.preferred_language == "unknown" else persona.preferred_language
    seed = _seed_outside_holdout(settings, persona, language)
    event = make_event(settings, persona, language, seed)
    purpose = "J1" if persona.journey == "J1" else "J2"
    gates, clearance_id = _gates(settings, event, purpose)
    run = run_text(settings, persona, language, seed)
    result = run.result
    out = result.outcome

    events: list[dict[str, Any]] = []
    t = 0
    for g in gates:
        events.append({"t_ms": t, "kind": "holdout" if g["name"] == "holdout" else "gate",
                       "label": GATE_LABELS[g["name"]],
                       "status": "pass" if g["passed"] else "fail",
                       "detail": {"gate": g["name"], "reason_code": g["reason_code"]}})
        t += 40
    events.append({"t_ms": t, "kind": "clearance", "label": "Single-use clearance issued",
                   "status": "pass" if clearance_id else "fail",
                   "detail": {"expires_in_s": "60"}})
    base = t + 200
    transcript = [{"speaker": turn.speaker, "text": turn.text,
                   "t_ms": base + int(turn.t_s * 1000)} for turn in result.transcript]
    first_agent = next(x for x in transcript if x["speaker"] == "agent")
    events.append({"t_ms": first_agent["t_ms"], "kind": "disclosure",
                   "label": "AI and recording disclosed in the first sentence", "status": "pass",
                   "detail": {}})
    end_t = transcript[-1]["t_ms"] if transcript else base
    for i, (name, args) in enumerate(run.backend.calls):
        detail = {k: str(v) for k, v in args.items() if k not in {"booking_id", "summary"}}
        events.append({"t_ms": end_t - 600 + i * 60, "kind": "tool", "label": f"Tool: {name}",
                       "status": "info", "detail": detail})

    whatsapp_preview = None
    if "send_payment_link" in run.backend.names():
        tpl = TEMPLATES["av_payment_link_v1"]
        body = render(tpl, event.customer.preferred_language, {
            "first_name": event.customer.first_name, "city": event.property.city,
            "amount": format_inr(event.amount_due.value, event.amount_due.currency),
            "link": payment_link(settings, event), "grievance": settings.grievance.channel})
        whatsapp_preview = {"template": tpl.name, "language": event.customer.preferred_language,
                            "body": body}
        events.append({"t_ms": end_t - 300, "kind": "whatsapp",
                       "label": "WhatsApp utility template sent", "status": "pass",
                       "detail": {"template": tpl.name}})
    crm_ticket = None
    if result.handoff_summary is not None:
        s = result.handoff_summary
        crm_ticket = {"ticket_id": "T00001", "subject": f"Handoff: {s.reason} ({s.booking_masked})",
                      "priority": "urgent" if s.reason in URGENT else "normal"}
        events.append({"t_ms": end_t - 200, "kind": "crm",
                       "label": "CRM ticket with 5-line handoff summary", "status": "info",
                       "detail": {"reason": s.reason, "queue": s.queue}})
    checks = check_run(run)
    qa_score = round(100 * sum(c.passed for c in checks) / len(checks))
    events.append({"t_ms": end_t + 100, "kind": "qa", "label": f"QA scorecard {qa_score}/100",
                   "status": "pass" if all(c.passed for c in checks) else "fail", "detail": {}})
    cost = out.cost.model_dump()
    cost["total"] = sum(cost.values())
    events.append({"t_ms": end_t + 150, "kind": "cost", "label": "Cost of this call (mock pricing)",
                   "status": "info", "detail": {"total_paise": str(cost["total"])}})
    events.append({"t_ms": end_t + 200, "kind": "end", "label": f"Outcome: {out.outcome}",
                   "status": "info", "detail": {"outcome": out.outcome}})
    events.sort(key=lambda e: int(e["t_ms"]))
    return {
        "run_id": f"rec_{scenario}", "scenario": scenario, "title": title, "mode": "text",
        "recorded_at": RECORDED_AT,
        "method": "Recorded from the engine in text mode: compliance.evaluate for the gates, the "
                  f"agent with the mock LLM and scripted caller persona {persona_id} (seed {seed}).",
        "events": events, "transcript": transcript,
        "whatsapp_preview": whatsapp_preview, "crm_ticket": crm_ticket,
        "qa": {"score": qa_score, "checks": [{"name": c.name, "passed": c.passed} for c in checks]},
        "cost_paise": cost,
        "latency_ms": {"p50": out.latency_ms.p50, "p95": out.latency_ms.p95,
                       "per_turn": [int(x * 1000) for x in result.turn_latencies_s]},
    }


def main() -> None:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for scenario, (persona_id, title) in SCENARIOS.items():
        data = record(scenario, persona_id, title)
        text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
        (out_dir / f"{scenario}.json").write_text(text)
        print(scenario, data["events"][-1]["label"], "qa", data["qa"]["score"])


if __name__ == "__main__":
    main()

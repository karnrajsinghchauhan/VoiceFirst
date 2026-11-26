"""Turns one engine run into the /demo timeline. Every entry comes from what the engine did."""

from __future__ import annotations

from app.api.ports import (
    DemoCheck,
    DemoCost,
    DemoEvent,
    DemoLatency,
    DemoQa,
    DemoRun,
    DemoScenario,
    DemoTicket,
    DemoTurn,
    DemoWhatsApp,
)
from app.contracts.generated.call_outcome import CallOutcome
from app.demo.engine import EngineRun
from app.messaging.templates import TEMPLATES, render
from app.simulator.assertions import check_run
from app.simulator.caller import Persona
from app.simulator.scenario import Run
from app.voice.agent import ConversationResult
from app.voice.tools import RecordingToolBackend

METHOD = (
    "Real dispatcher, gates, agent and post-call on an isolated in-memory engine with mock "
    "providers and a scripted caller. Times are engine milliseconds; provider latency is "
    "not included until real keys (M8)."
)

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


def _gate_events(run: EngineRun) -> list[DemoEvent]:
    events: list[DemoEvent] = []
    for p in run.bus.log:
        if p.topic != "av.gate-decisions.v1":
            continue
        gates = p.record["gates"]
        assert isinstance(gates, list)
        for g in gates:
            events.append(
                DemoEvent(
                    t_ms=p.t_ms,
                    kind="holdout" if g["name"] == "holdout" else "gate",
                    label=GATE_LABELS[str(g["name"])],
                    status="pass" if g["passed"] else "fail",
                    detail={"gate": str(g["name"]), "reason_code": str(g["reason_code"])},
                )
            )
        clearance = p.record["clearance_id"]
        if clearance is not None:
            events.append(
                DemoEvent(
                    t_ms=p.t_ms,
                    kind="clearance",
                    label="GateClearance issued (single use, 60 s)",
                    status="pass",
                    detail={"clearance_id": str(clearance)},
                )
            )
    return events


def _call_t_ms(run: EngineRun) -> int:
    return next((p.t_ms for p in run.bus.log if p.topic == "av.call-outcomes.v1"), 0)


def _whatsapp(run: EngineRun) -> DemoWhatsApp | None:
    sent = [m for m in run.runtime.providers.whatsapp.sent if "template" in m]  # type: ignore[attr-defined]
    if not sent:
        return None
    msg = sent[0]
    name, language, params = str(msg["template"]), msg["language"], msg["params"]
    assert isinstance(params, dict)
    body = render(TEMPLATES[name], language, {k: str(v) for k, v in params.items()})
    return DemoWhatsApp(template=name, language=str(language), body=body)


def _ticket(run: EngineRun) -> DemoTicket | None:
    tickets = run.runtime.providers.crm.tickets  # type: ignore[attr-defined]
    if not tickets:
        return None
    ticket_id, t = next(iter(tickets.items()))
    return DemoTicket(ticket_id=ticket_id, subject=str(t["subject"]), priority=str(t["priority"]))


def _qa(run: EngineRun, persona: Persona, result: ConversationResult) -> DemoQa:
    checks = check_run(
        Run(
            persona=persona,
            language=run.event.customer.preferred_language,
            seed=0,
            event=run.event,
            result=result,
            backend=RecordingToolBackend(),
            replay_key="demo",
        )
    )
    score = round(100 * sum(c.passed for c in checks) / len(checks))
    return DemoQa(score=score, checks=[DemoCheck(name=c.name, passed=c.passed) for c in checks])


def _call_events(
    t: int,
    out: CallOutcome,
    result: ConversationResult,
    wa: DemoWhatsApp | None,
    ticket: DemoTicket | None,
    qa: DemoQa,
    cost: DemoCost,
) -> list[DemoEvent]:
    first = next(turn.text for turn in result.transcript if turn.speaker == "agent")
    events = [
        DemoEvent(
            t_ms=t,
            kind="disclosure",
            label="AI and recording disclosed",
            status="pass" if "AI" in first else "fail",
            detail={"text": first},
        )
    ]
    events += [
        DemoEvent(
            t_ms=t, kind="tool", label=c.name, status="info", detail={"result": c.result_code}
        )
        for c in out.tools_called
    ]
    if out.sensitive_data_spoken:
        events.append(
            DemoEvent(
                t_ms=t,
                kind="tool",
                label="card or OTP redacted",
                status="pass",
                detail={"redaction_applied": str(out.redaction_applied)},
            )
        )
    if wa is not None:
        events.append(
            DemoEvent(
                t_ms=t,
                kind="whatsapp",
                label=f"WhatsApp {wa.template}",
                status="pass",
                detail={"language": wa.language},
            )
        )
    if ticket is not None:
        events.append(
            DemoEvent(
                t_ms=t,
                kind="crm",
                label=f"CRM ticket {ticket.ticket_id}",
                status="info",
                detail={"subject": ticket.subject},
            )
        )
    events.append(
        DemoEvent(
            t_ms=t,
            kind="qa",
            label=f"QA score {qa.score}",
            status="pass" if qa.score == 100 else "fail",
            detail={"checks": len(qa.checks)},
        )
    )
    events.append(
        DemoEvent(
            t_ms=t,
            kind="cost",
            label=f"Cost {cost.total} paise",
            status="info",
            detail={"total_paise": cost.total},
        )
    )
    events.append(
        DemoEvent(
            t_ms=t,
            kind="end",
            label=f"Outcome: {out.outcome}",
            status="info",
            detail={"outcome": out.outcome},
        )
    )
    return events


def _no_call(run_id: str, scenario: DemoScenario, run: EngineRun) -> DemoRun:
    events = _gate_events(run)
    if run.queue_reason == "kill_switch_engaged":
        events.append(
            DemoEvent(
                t_ms=0,
                kind="gate",
                label="kill switch engaged",
                status="fail",
                detail={"reason": "queue dropped, no dial"},
            )
        )
    events.append(
        DemoEvent(
            t_ms=0,
            kind="end",
            label="No call placed",
            status="info",
            detail={"reason": run.queue_reason},
        )
    )
    return DemoRun(
        run_id=run_id,
        scenario=scenario,
        mode="text",
        method=METHOD,
        events=events,
        transcript=[],
        whatsapp_preview=None,
        crm_ticket=None,
        qa=DemoQa(score=0, checks=[]),
        cost_paise=DemoCost(telephony=0, stt=0, tts=0, llm=0, whatsapp=0, total=0),
        latency_ms=DemoLatency(p50=0, p95=0, per_turn=[]),
    )


def build_run(run_id: str, scenario: DemoScenario, run: EngineRun, persona: Persona) -> DemoRun:
    result = run.result
    if result is None:
        return _no_call(run_id, scenario, run)
    out = result.outcome
    t = _call_t_ms(run)
    c = out.cost
    cost = DemoCost(
        telephony=c.telephony,
        stt=c.stt,
        tts=c.tts,
        llm=c.llm,
        whatsapp=c.whatsapp,
        total=c.telephony + c.stt + c.tts + c.llm + c.whatsapp,
    )
    wa, ticket, qa = _whatsapp(run), _ticket(run), _qa(run, persona, result)
    return DemoRun(
        run_id=run_id,
        scenario=scenario,
        mode="text",
        method=METHOD,
        events=_gate_events(run) + _call_events(t, out, result, wa, ticket, qa, cost),
        transcript=[
            DemoTurn(speaker=turn.speaker, text=turn.text, t_ms=t) for turn in result.transcript
        ],
        whatsapp_preview=wa,
        crm_ticket=ticket,
        qa=qa,
        cost_paise=cost,
        latency_ms=DemoLatency(
            p50=out.latency_ms.p50,
            p95=out.latency_ms.p95,
            per_turn=[round(s * 1000) for s in result.turn_latencies_s],
        ),
    )

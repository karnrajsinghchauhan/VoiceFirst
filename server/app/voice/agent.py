"""Text-mode conversation engine for J1 (payment rescue) and J2 (pre-arrival confirmation).

Design (D-009): a deterministic core chooses each agent act and the tools it
needs from the customer's Signals; the LLM phrases the acts and must return
exactly the requested tool calls. Every agent utterance then passes the
dark-pattern filter, the read-back verifier and the PII check before it is
spoken. Any AgodaVoiceError mid-call takes the single error path: apology,
human callback, alert, outcome=error (11.11). The engine never switches
provider.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.call_outcome import (
    CallOutcome,
    Cost,
    Handoff,
    LatencyMs,
    ToolsCalledItem,
)
from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import (
    AgodaVoiceError,
    PurposeFieldViolationError,
    ReadBackMismatchError,
    ToolNotAllowedError,
)
from app.core.ids import mask_booking_id, sha256_hex
from app.core.redaction import redact_text
from app.core.types import Language, Purpose
from app.providers.base import ChatMessage, LlmProvider, ToolCall
from app.providers.llm.mock import STATE_PREFIX
from app.voice import prompts
from app.voice.context import PurposeContext
from app.voice.dark_patterns import assert_clean
from app.voice.guardrails import Signals, classify
from app.voice.normalise import (
    CURRENCY_WORDS,
    amount_words,
    date_words,
    number_word_set,
    number_words,
    spoken_lang,
    words_to_number,
)
from app.voice.tools import TOOL_SPECS, ToolBackend, check_allowed, ledger_entry

Outcome = Literal[
    "link_sent",
    "details_confirmed",
    "callback_scheduled",
    "handed_off",
    "opted_out",
    "wrong_person",
    "minor_on_line",
    "no_answer",
    "voicemail",
    "abandoned",
    "error",
]

MAX_AGENT_TURNS = 14
FILLER_THRESHOLD_S = 0.7
ANGER_THRESHOLD = 0.7
# Telephony unit price is [CD] (Plivo India Rs 0.38/min, 30-s pulse); STT/TTS from Sarvam (S-31).
_TELEPHONY_PAISE_PER_PULSE = 19
_STT_PAISE_PER_MIN = 49
_TTS_PAISE_PER_1000_CHARS = 300


@dataclass(frozen=True)
class Heard:
    """What the agent heard in one customer turn (already through STT in audio mode)."""

    text: str
    overlap: bool = False
    stt_s: float = 0.0
    endpoint_s: float = 0.0


class Listener(Protocol):
    """The customer side of the call: the synthetic caller in evals, the media path in production."""

    def listen(self, act: str, agent_text: str) -> Heard: ...


@dataclass(frozen=True)
class TranscriptTurn:
    speaker: Literal["agent", "customer"]
    text: str
    act: str
    language: Language
    t_s: float


@dataclass
class ConversationResult:
    outcome: CallOutcome
    transcript: list[TranscriptTurn]
    handoff_summary: HandoffSummary | None
    error_code: str | None
    asks: list[tuple[str, bool]]
    turn_latencies_s: list[float]
    acts: list[str]


@dataclass
class CallSetup:
    event: BookingEvent
    purpose: Purpose
    call_id: str
    clearance_id: str
    cli: str
    settings: Settings
    clock: Clock
    llm: LlmProvider
    backend: ToolBackend
    listener: Listener
    is_killed: Callable[[], bool]
    monotonic: Callable[[], float]
    model_ids: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Step:
    acts: tuple[str, ...]
    tools: tuple[ToolCall, ...] = ()
    end: Outcome | None = None
    stage: str | None = None


class _End(Exception):  # noqa: N818 - control flow, not an error
    """Internal control flow: the call has reached an outcome."""

    def __init__(self, outcome: Outcome) -> None:
        self.outcome = outcome


def _end_call(outcome: str) -> ToolCall:
    return ToolCall("end_call", {"outcome": outcome})


_AFTER_SPEECH = frozenset({"warm_transfer", "end_call"})
_IST = ZoneInfo("Asia/Kolkata")
_CURRENCY_RX = re.compile(r"₹|\bRs\.?\s?\d|\bINR\b|\d+\s*(rupaye|rupees|रुपये)", re.IGNORECASE)
_HANDOFF_QUEUE = {
    "vip": "vip",
    "emergency": "priority",
    "dispute": "disputes",
    "money_request": "payments",
    "booking_change": "bookings",
}


class Conversation:
    def __init__(self, setup: CallSetup) -> None:
        self.s = setup
        self.ctx = PurposeContext(setup.event, setup.purpose)
        pref = self.ctx.get("customer.preferred_language")
        self.lang: Language = "hinglish" if pref == "unknown" else pref
        self.detected: Language = "unknown"
        self.stage = "await_link_consent" if setup.purpose == "J1" else "await_start_consent"
        self.fails: dict[str, int] = {}
        self.anger_streak = 0
        self.injections = 0
        self.vip_pending = bool(self.ctx.get("flags.vip"))
        self.first_customer_turn = True
        self.transcript: list[TranscriptTurn] = []
        self.ledger: list[ToolsCalledItem] = []
        self.cost_whatsapp = 0
        self.sensitive_spoken = False
        self.redaction_applied = False
        self.handoff: HandoffSummary | None = None
        self.handoff_reason: str | None = None
        self.asks: list[tuple[str, bool]] = []
        self.latencies: list[float] = []
        self.acts: list[str] = []
        self.last_agent_act = ""
        self.disclosure_at = setup.clock.now()
        self.started_at = setup.clock.now()
        self.amd: Literal["human", "machine-vm", "not_run"] = "not_run"
        self.customer_wants = "follow up on the booking"
        self._stage_before_minor = self.stage

    # ---- values the lines may use (purpose-limited) ----
    def _values(self) -> dict[str, str]:
        ctx = self.ctx
        values = {
            "first_name": str(ctx.get("customer.first_name")),
            "city": str(ctx.get("property.city")),
            "property_name": str(ctx.get("property.name")),
            "booking_tail": str(ctx.get("booking_id"))[-4:],
        }
        values["check_in_date"] = date_words(
            date.fromisoformat(ctx.get("stay.check_in")), self.lang
        )
        if self.s.purpose == "J1":
            amount = ctx.get("amount_due")
            values["amount"] = amount_words(amount["value"], amount["currency"], self.lang)
            due = ctx.get("payment_due_at")
            if due is not None:
                local = datetime.fromisoformat(due).astimezone(_IST)
                values["due_date"] = date_words(local.date(), self.lang)
        else:
            values["check_out_date"] = date_words(
                date.fromisoformat(ctx.get("stay.check_out")), self.lang
            )
            values["guests"] = number_words(int(ctx.get("stay.guests")), self.lang)
        return values

    # ---- agent speech ----
    def _say(self, step: _Step) -> None:
        if self.s.is_killed():
            step = _Step(
                ("kill_close",), (ToolCall("end_call", {"outcome": "abandoned"}),), "abandoned"
            )
        t0 = self.s.monotonic()
        state = {
            "acts": list(step.acts),
            "language": spoken_lang(self.lang),
            "values": self._values(),
            "tools": [{"name": t.name, "args": t.args} for t in step.tools],
            "stage": self.stage,
            "purpose": self.s.purpose,
            "allowed_tools": sorted(t.name for t in TOOL_SPECS),
        }
        messages = [ChatMessage("system", prompts.system_prompt())]
        for turn in self.transcript:
            messages.append(
                ChatMessage("assistant" if turn.speaker == "agent" else "user", turn.text)
            )
        messages.append(ChatMessage("system", STATE_PREFIX + json.dumps(state, ensure_ascii=False)))
        llm_turn = self.s.llm.next_turn(messages, list(TOOL_SPECS))
        self._check_tool_calls(llm_turn.tool_calls, step.tools)
        utterance = llm_turn.utterance
        self._verify_utterance(utterance)
        # Transfers and hang-ups happen after the line is spoken; everything else before,
        # because the line reports its result.
        before = [c for c in step.tools if c.name not in _AFTER_SPEECH]
        after = [c for c in step.tools if c.name in _AFTER_SPEECH]
        slow = False
        for call in before:
            tool_t0 = self.s.monotonic()
            self._run_tool(call)
            slow = slow or self.s.monotonic() - tool_t0 > FILLER_THRESHOLD_S
        latency = self.s.monotonic() - t0
        if slow and self.last_agent_act != "filler":
            # The filler is spoken while the tool runs; never two fillers in a row (10.7).
            self._emit("filler", prompts.render("filler", self.lang, {}), latency)
        if utterance:
            self._emit("+".join(step.acts), utterance, latency)
        for call in after:
            self._run_tool(call)
        if step.stage is not None:
            self.stage = step.stage
        if step.end is not None:
            raise _End(step.end)

    def _emit(self, act: str, text: str, latency: float) -> None:
        self.latencies.append(latency)
        self.acts.append(act)
        self.last_agent_act = act
        self.transcript.append(TranscriptTurn("agent", text, act, self.lang, self.s.monotonic()))

    def _check_tool_calls(
        self, proposed: tuple[ToolCall, ...], required: tuple[ToolCall, ...]
    ) -> None:
        for call in proposed:
            check_allowed(call.name)
        if [(c.name, c.args) for c in proposed] != [(c.name, c.args) for c in required]:
            raise ToolNotAllowedError("LLM proposed tool calls the current state does not permit")

    def _verify_utterance(self, text: str) -> None:
        assert_clean(text)
        if _CURRENCY_RX.search(text):
            raise ReadBackMismatchError(
                "amounts must be spoken in words, never as digits or symbols"
            )
        event = self.s.event
        if event.booking_id in text or event.customer.phone_e164[3:] in text or "@" in text:
            raise PurposeFieldViolationError("utterance contains a full identifier")
        self._verify_amounts(text)

    def _verify_amounts(self, text: str) -> None:
        """Every spoken amount must equal booking.amount_due (REQ-PAY-03)."""
        lang = spoken_lang(self.lang)
        unit = CURRENCY_WORDS["INR"][lang][0]
        tokens = text.replace(",", " ").replace(".", " ").replace("-", " ").split()
        vocab = number_word_set(self.lang)
        for i, tok in enumerate(tokens):
            if tok != unit:
                continue
            j = i
            while j > 0 and tokens[j - 1] in vocab:
                j -= 1
            if j == i:
                raise ReadBackMismatchError("currency word without an amount")
            spoken = words_to_number(" ".join(tokens[j:i]), self.lang)
            if self.s.purpose != "J1":
                raise ReadBackMismatchError("J2 must not speak amounts")
            due = self.ctx.get("amount_due")
            if spoken != int(float(due["value"])):
                raise ReadBackMismatchError(f"spoken amount {spoken} != amount_due {due['value']}")

    def _run_tool(self, call: ToolCall) -> None:
        b, e, cid = self.s.backend, self.s.event, self.s.call_id
        name = call.name
        if name == "send_payment_link":
            result = b.send_payment_link(cid, e)
        elif name == "send_app_link":
            result = b.send_app_link(cid, e)
        elif name == "confirm_details":
            result = b.confirm_details(cid, e, dict(call.args))
        elif name == "record_special_request":
            result = b.record_special_request(cid, e, call.args["text"])
        elif name == "log_case":
            result = b.log_case(cid, e, call.args["category"], call.args["summary"])
        elif name == "schedule_callback":
            result = b.schedule_callback(cid, e, call.args["reason"], call.args["when"])
        elif name == "mark_dnc":
            result = b.mark_dnc(cid, e)
        elif name == "end_call":
            result = b.end_call(cid, call.args["outcome"])
        elif name == "warm_transfer":
            summary = self._handoff_summary(call.args["reason"], call.args["queue"])
            transfer = b.warm_transfer(cid, e, summary)
            self.handoff = summary
            self.ledger.append(
                ledger_entry(
                    name, dict(call.args), "connected" if transfer.connected else "no_human"
                )
            )
            if not transfer.connected:
                raise _NoHuman()
            return
        else:
            raise ToolNotAllowedError(f"{name} has no handler")
        self.cost_whatsapp += result.cost_paise
        self.ledger.append(ledger_entry(name, dict(call.args), result.code))

    def _handoff_summary(self, reason: str, queue: str) -> HandoffSummary:
        now = self.s.clock.now()
        sentiment: Literal["calm", "concerned", "angry", "distressed"] = (
            "distressed"
            if reason == "emergency"
            else "angry"
            if self.anger_streak or reason in ("anger", "dispute")
            else "concerned"
            if reason in ("money_request", "repeated_failure", "booking_change")
            else "calm"
        )
        did = ", ".join(sorted({t.name for t in self.ledger})) or "disclosed AI and recording"
        policy = {
            "money_request": ["P1 AI never moves money", "REQ-CP-02"],
            "dispute": ["P2 disputes stay with humans"],
            "emergency": ["P2 medical/death/safety"],
            "vip": ["P2 VIP flag"],
        }.get(reason, ["P2 human one sentence away"])
        return HandoffSummary(
            schema_version="1.0.0",
            tenant_id=self.s.event.tenant_id,
            trace_id=self.s.event.trace_id,
            call_id=self.s.call_id,
            who=f"{self.ctx.get('customer.first_name')} ({self.detected if self.detected != 'unknown' else self.lang})",
            booking_masked=mask_booking_id(self.s.event.booking_id),
            customer_wants=self.customer_wants,
            ai_did=f"Disclosed AI and recording; {did}",
            sentiment=sentiment,
            policy_refs=policy,
            next_best_action={
                "money_request": "Review refund/cancellation request against booking policy",
                "dispute": "Investigate the dispute; do not let the AI respond",
                "emergency": "Call back immediately with empathy; consider waiving per policy",
                "vip": "Serve as VIP per AgodaVIP rules [CD]",
                "booking_change": "Amend the booking details the customer reported",
            }.get(reason, "Resolve the customer's request"),
            reason=reason,
            queue=queue,
            sla_ack_due_at=now + timedelta(hours=48),
            sla_resolve_due_at=now + timedelta(days=30),
        )

    # ---- turn handling ----
    def _handoff(self, reason: str, lead_act: str, category: str) -> _Step:
        self.handoff_reason = reason
        queue = _HANDOFF_QUEUE.get(category, "general")
        tools = (
            ToolCall("log_case", {"category": category, "summary": self.customer_wants}),
            ToolCall("warm_transfer", {"reason": reason, "queue": queue}),
        )
        return _Step((lead_act,), tools, end="handed_off")

    def _fail(self, reask: str) -> _Step:
        count = self.fails.get(self.stage, 0) + 1
        self.fails[self.stage] = count
        if count >= 2:
            self.customer_wants = "could not complete the step after two attempts"
            return self._handoff("repeated_failure", "handoff", "repeated_failure")
        return _Step((reask,))

    def _resume_act(self) -> str:
        """The current step's question, asked plainly after a side topic (bot question, warning)."""
        return {
            "await_link_consent": "j1_ask",
            "await_start_consent": "j2_resume",
            "confirm_stay": "j2_confirm_stay",
            "ask_arrival": "j2_ask_arrival",
            "ask_request": "j2_ask_request",
        }[self.stage]

    def _reask_act(self) -> str:
        """The current step's question after an unclear answer."""
        return {
            "await_link_consent": "j1_reask",
            "await_start_consent": "j2_resume",
            "confirm_stay": "j2_reask_stay",
            "ask_arrival": "j2_ask_arrival",
            "ask_request": "j2_ask_request",
        }[self.stage]

    def _decide(self, sig: Signals, redacted: str) -> _Step:
        first = self.first_customer_turn
        self.first_customer_turn = False
        self.anger_streak = self.anger_streak + 1 if sig.anger >= ANGER_THRESHOLD else 0

        if first and sig.machine:
            self.amd = "machine-vm"
            # Nothing is left on a voicemail: a message would disclose the booking to whoever plays it.
            return _Step((), (_end_call("voicemail"),), end="voicemail")
        if first:
            self.amd = "human"
        if sig.emergency:
            self.customer_wants = "medical emergency, death or safety concern"
            return self._handoff("emergency", "emergency", "emergency")
        if sig.opt_out:
            self.customer_wants = "opt out of calls"
            return _Step(
                ("opt_out",), (ToolCall("mark_dnc", {}), _end_call("opted_out")), end="opted_out"
            )
        if self.stage == "await_booker":
            if sig.yes and not (sig.minor or sig.booker_unavailable):
                self.stage = self._stage_before_minor
                return _Step(("identity_check",))
            return _Step(("minor_end",), (_end_call("minor_on_line"),), end="minor_on_line")
        if sig.minor or (first and self.ctx.get("flags.minor_suspected") and not sig.yes):
            self._stage_before_minor = self.stage
            return _Step(("minor_ask_booker",), stage="await_booker")
        if self.stage == "await_callback_time":
            when = redacted or "unspecified"
            return _Step(
                ("third_party_close",),
                (
                    ToolCall("schedule_callback", {"reason": "booker_unavailable", "when": when}),
                    _end_call("callback_scheduled"),
                ),
                end="callback_scheduled",
            )
        if sig.wrong_number:
            return _Step(("wrong_person",), (_end_call("wrong_person"),), end="wrong_person")
        if sig.third_party:
            return _Step(("third_party",), stage="await_callback_time")
        if sig.payment_credential:
            self.sensitive_spoken = True
            return _Step(("credential_warning", self._resume_act()))
        if sig.wants_human:
            self.customer_wants = "asked to speak to a human"
            return self._handoff("customer_request", "handoff", "customer_request")
        if sig.dispute:
            self.customer_wants = "dispute, legal or payment-deduction complaint"
            return self._handoff("dispute", "handoff", "dispute")
        if sig.injection:
            self.injections += 1
            if self.injections >= 2:
                self.customer_wants = "repeated attempts to override the assistant"
                return self._handoff("injection_repeat", "handoff", "abuse")
            return _Step(("injection_once", self._resume_act()))
        if sig.money_request:
            self.customer_wants = "refund, cancellation or price change"
            return self._handoff("money_request", "refund_cancel", "money_request")
        if self.anger_streak >= 2:
            self.customer_wants = "customer upset"
            return self._handoff("anger", "handoff", "anger")
        if self.vip_pending:
            self.vip_pending = False
            self.customer_wants = "VIP customer"
            return self._handoff("vip", "vip", "vip")
        if sig.bot_question:
            return _Step(("bot_answer", self._resume_act()))
        if sig.add_on:
            if self.s.event.customer.whatsapp_opt_in is None:
                return _Step(("addon_no_whatsapp", self._resume_act()))
            return _Step(("addon_app_link", self._resume_act()), (ToolCall("send_app_link", {}),))
        if sig.silence:
            return self._fail("reprompt_silence")
        if self.s.purpose == "J1":
            return self._decide_j1(sig)
        return self._decide_j2(sig, redacted)

    def _decide_j1(self, sig: Signals) -> _Step:
        end_tool = ToolCall("end_call", {"outcome": "link_sent"})
        if sig.bnpl_confusion and not sig.yes:
            return _Step(("bnpl_explain",))
        if sig.yes:
            self.asks.append(("payment_link", False))
            if self.s.event.customer.whatsapp_opt_in is None:
                return _Step(
                    ("j1_no_whatsapp", "close"),
                    (ToolCall("end_call", {"outcome": "abandoned"}),),
                    end="abandoned",
                )
            line = (
                "j1_link_sent"
                if self.ctx.get("payment_due_at") is not None
                else "j1_link_sent_nodue"
            )
            return _Step(
                (line, "close"), (ToolCall("send_payment_link", {}), end_tool), end="link_sent"
            )
        if sig.no:
            # A refused ask is never repeated (REQ-CP-02).
            self.asks.append(("payment_link", True))
            return _Step(
                ("j1_declined", "close"),
                (ToolCall("end_call", {"outcome": "abandoned"}),),
                end="abandoned",
            )
        if sig.clarify:
            return _Step(("identity_check",))
        if sig.question:
            return _Step(("unknown_question", "j1_ask"))
        return self._fail("j1_reask")

    def _decide_j2(self, sig: Signals, redacted: str) -> _Step:
        end_ok = ToolCall("end_call", {"outcome": "details_confirmed"})
        if self.stage == "await_start_consent":
            if sig.yes:
                return _Step(("j2_confirm_stay",), stage="confirm_stay")
            if sig.no:
                self.asks.append(("confirm_details", True))
                return _Step(
                    ("close",), (ToolCall("end_call", {"outcome": "abandoned"}),), end="abandoned"
                )
        elif self.stage == "confirm_stay":
            if sig.yes:
                details = {"check_in": "confirmed", "check_out": "confirmed", "guests": "confirmed"}
                return _Step(
                    ("j2_ask_arrival",),
                    (ToolCall("confirm_details", details),),
                    stage="ask_arrival",
                )
            if sig.no:
                self.customer_wants = "stay details are wrong; wants a change"
                return self._handoff("booking_change", "j2_mismatch", "booking_change")
        elif self.stage == "ask_arrival":
            if redacted and not sig.question:
                return _Step(
                    ("j2_ask_request",),
                    (ToolCall("record_special_request", {"text": f"arrival time: {redacted}"}),),
                    stage="ask_request",
                )
        elif self.stage == "ask_request":
            if sig.nothing or (sig.no and not sig.yes):
                return _Step(("close",), (end_ok,), end="details_confirmed")
            if redacted and not sig.question:
                return _Step(
                    ("j2_request_noted", "close"),
                    (ToolCall("record_special_request", {"text": redacted}), end_ok),
                    end="details_confirmed",
                )
        if sig.clarify:
            return _Step(("identity_check",))
        if sig.question:
            return _Step(("unknown_question", self._resume_act()))
        return self._fail(self._reask_act())

    def _hear(self) -> tuple[Signals, str]:
        heard = self.s.listener.listen(self.last_agent_act, self.transcript[-1].text)
        sig = classify(heard.text, heard.overlap)
        redacted = redact_text(heard.text)
        if redacted != heard.text:
            self.redaction_applied = True
        if sig.language != "unknown":
            self.detected = sig.language
            self.lang = sig.language
        self.transcript.append(
            TranscriptTurn("customer", redacted, "", sig.language, self.s.monotonic())
        )
        return sig, redacted

    def run(self) -> Outcome:
        opening = "j1_opening" if self.s.purpose == "J1" else "j2_opening"
        self.disclosure_at = self.s.clock.now()
        self._say(_Step((opening,)))
        if self.s.purpose == "J1":
            self.asks.append(("payment_link", False))
        for _ in range(MAX_AGENT_TURNS):
            sig, redacted = self._hear()
            self._say(self._decide(sig, redacted))
        self.customer_wants = "conversation did not converge"
        self._say(self._handoff("turn_limit", "handoff", "turn_limit"))
        raise AssertionError("unreachable: handoff always ends the call")


class _NoHuman(Exception):  # noqa: N818 - control flow, not an error
    """warm_transfer found no human; the engine says so and schedules a callback (P2)."""


def run_conversation(setup: CallSetup) -> ConversationResult:
    """Runs one call to an outcome. Raises nothing for in-call failures: those take the error path."""
    conv = Conversation(setup)
    error_code: str | None = None
    try:
        conv.run()
    except _End as end:
        outcome: Outcome = end.outcome
    except _NoHuman:
        outcome = _no_human_path(conv)
    except AgodaVoiceError as exc:
        error_code = exc.code
        outcome = _error_path(conv, exc)
    return _result(conv, outcome, error_code)


def _no_human_path(conv: Conversation) -> Outcome:
    conv._emit("no_human", prompts.render("no_human", conv.lang, {}), 0.0)
    reason = conv.handoff_reason or "no_human"
    for call in (
        ToolCall("schedule_callback", {"reason": f"no_human:{reason}", "when": "next_available"}),
        ToolCall("end_call", {"outcome": "callback_scheduled"}),
    ):
        conv._run_tool(call)
    return "callback_scheduled"


def _error_path(conv: Conversation, exc: AgodaVoiceError) -> Outcome:
    """Apology, human callback, alert (11.11). Lines are rendered without the LLM, which may be the failure."""
    s = conv.s
    s.backend.alert(s.call_id, exc.code, str(exc))
    conv._emit("error_apology", prompts.render("error_apology", conv.lang, {}), 0.0)
    callback = ToolCall(
        "schedule_callback", {"reason": f"error:{exc.code}", "when": "next_available"}
    )
    conv._run_tool(callback)
    conv._run_tool(ToolCall("end_call", {"outcome": "error"}))
    return "error"


def _result(conv: Conversation, outcome: Outcome, error_code: str | None) -> ConversationResult:
    s = conv.s
    agent_chars = sum(len(t.text) for t in conv.transcript if t.speaker == "agent")
    customer_words = sum(len(t.text.split()) for t in conv.transcript if t.speaker == "customer")
    seconds = agent_chars / 15 + customer_words / 2.5
    pulses = max(1, int(-(-seconds // 30)))
    lat_ms = sorted(int(x * 1000) for x in conv.latencies) or [0]
    p50 = lat_ms[len(lat_ms) // 2]
    p95 = lat_ms[min(len(lat_ms) - 1, int(round(0.95 * (len(lat_ms) - 1))))]
    transcript_text = "\n".join(f"{t.speaker}: {t.text}" for t in conv.transcript)
    provenance = sha256_hex(
        json.dumps(
            {
                "call_id": s.call_id,
                "prompt_version": prompts.PROMPT_VERSION,
                "model_ids": s.model_ids,
                "transcript": transcript_text,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )
    handoff = None
    if conv.handoff is not None:
        h = conv.handoff
        summary = "\n".join(
            [
                f"Who: {h.who}",
                f"Booking: {h.booking_masked}; wants: {h.customer_wants}",
                f"AI did: {h.ai_did}",
                f"Sentiment: {h.sentiment}; policy: {', '.join(h.policy_refs)}",
                f"Next: {h.next_best_action}",
            ]
        )
        handoff = Handoff(reason=h.reason, summary=summary, queue=h.queue)
    outcome_record = CallOutcome(
        schema_version="1.0.0",
        tenant_id=s.event.tenant_id,
        trace_id=s.event.trace_id,
        call_id=s.call_id,
        clearance_id=s.clearance_id,
        booking_id=s.event.booking_id,
        purpose=s.purpose,
        cli=s.cli,
        started_at=conv.started_at,
        answered=True,
        amd_result=conv.amd,
        language_detected=conv.detected,
        disclosure_played_at=conv.disclosure_at,
        turns=len(conv.transcript),
        tools_called=conv.ledger,
        outcome=outcome,
        handoff=handoff,
        latency_ms=LatencyMs(p50=p50, p95=p95),
        cost=Cost(
            telephony=pulses * _TELEPHONY_PAISE_PER_PULSE,
            stt=int(customer_words / 2.5 / 60 * _STT_PAISE_PER_MIN + 0.999),
            tts=int(agent_chars * _TTS_PAISE_PER_1000_CHARS / 1000 + 0.999),
            llm=0,
            whatsapp=conv.cost_whatsapp,
        ),
        redaction_applied=conv.redaction_applied,
        sensitive_data_spoken=conv.sensitive_spoken,
        grievance_channel=s.settings.grievance.channel,
        ai_generated=True,
        model_ids=s.model_ids or {"llm": s.llm.model_id},
        provenance_hash=provenance,
    )
    return ConversationResult(
        outcome=outcome_record,
        transcript=conv.transcript,
        handoff_summary=conv.handoff,
        error_code=error_code,
        asks=conv.asks,
        turn_latencies_s=conv.latencies,
        acts=conv.acts,
    )

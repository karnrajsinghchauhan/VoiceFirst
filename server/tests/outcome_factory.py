"""Builders for post-call records (W-E)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.contracts.generated.call_outcome import CallOutcome
from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.ids import new_id, new_trace_id, sha256_hex
from app.handoff.summary import HandoffFacts, build_summary


def make_outcome(at: datetime, **overrides: Any) -> CallOutcome:
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tenant_id": "agoda-in",
        "trace_id": new_trace_id(),
        "call_id": new_id("call"),
        "clearance_id": new_id("clr"),
        "booking_id": "BK00001234",
        "purpose": "J1",
        "cli": "+911600123456",
        "started_at": at.isoformat(),
        "answered": True,
        "amd_result": "human",
        "language_detected": "hinglish",
        "disclosure_played_at": at.isoformat(),
        "turns": 6,
        "tools_called": [
            {"name": "send_payment_link", "args_hash": sha256_hex("a"), "result_code": "ok"}
        ],
        "outcome": "link_sent",
        "handoff": None,
        "latency_ms": {"p50": 640, "p95": 1100},
        "cost": {"telephony": 76, "stt": 98, "tts": 150, "llm": 40, "whatsapp": 14},
        "redaction_applied": True,
        "sensitive_data_spoken": False,
        "grievance_channel": "Agoda grievance officer",
        "ai_generated": True,
        "model_ids": {"llm": "mock", "tts": "mock"},
        "provenance_hash": sha256_hex("audio"),
    }
    data.update(overrides)
    return CallOutcome.model_validate(data)


def make_summary(at: datetime, **overrides: Any) -> HandoffSummary:
    facts: dict[str, Any] = {
        "tenant_id": "agoda-in",
        "trace_id": new_trace_id(),
        "call_id": new_id("call"),
        "first_name": "Priya",
        "purpose": "J1",
        "booking_id": "BK00001234",
        "customer_wants": "Refund for a double charge",
        "ai_did": "Logged case; did not promise a refund",
        "sentiment": "angry",
        "policy_refs": ("refunds-human-only",),
        "next_best_action": "Check payment gateway for duplicate capture",
        "reason": "dispute",
        "queue": "payments",
        "at": at,
    }
    facts.update(overrides)
    return build_summary(HandoffFacts(**facts))

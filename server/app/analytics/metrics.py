"""Pilot metrics (M6, 2.2): recovery, resolution time, CSAT, containment, cost per resolved contact.

All functions are pure over contract records; app/analytics/queries.py loads the inputs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from statistics import median, quantiles

from app.analytics.cost_model import whatsapp_utility_paise
from app.analytics.lift import InsufficientSampleError
from app.contracts.generated.call_outcome import CallOutcome

# The AI finished the job with no human: the journey's goal was met on the call.
AI_RESOLVED = frozenset({"link_sent", "details_confirmed"})
# A person (not a machine) was on the line, so the call could have been resolved.
REACHED = frozenset(
    {
        "link_sent",
        "details_confirmed",
        "callback_scheduled",
        "handed_off",
        "opted_out",
        "minor_on_line",
        "abandoned",
        "error",
    }
)


def rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise InsufficientSampleError("rate over an empty population")
    return numerator / denominator


def recovery_rate(recovered: Sequence[bool]) -> float:
    """Share of J1 bookings whose payment completed."""
    return rate(sum(recovered), len(recovered))


def containment(outcomes: Iterable[CallOutcome]) -> float:
    """AI-resolved share of calls that reached a person."""
    reached = [o for o in outcomes if o.outcome in REACHED]
    return rate(sum(o.outcome in AI_RESOLVED for o in reached), len(reached))


def containment_by(keyed: Iterable[tuple[Hashable, CallOutcome]]) -> dict[Hashable, float]:
    """Containment per persona, journey or language; keys with no reached call are left out."""
    groups: dict[Hashable, list[CallOutcome]] = defaultdict(list)
    for key, outcome in keyed:
        if outcome.outcome in REACHED:
            groups[key].append(outcome)
    return {key: containment(group) for key, group in groups.items()}


@dataclass(frozen=True)
class ResolutionSummary:
    n: int
    median: timedelta
    p90: timedelta


def resolution_time(durations: Sequence[timedelta]) -> ResolutionSummary:
    """Case-resolution time, Agoda's own headline metric (2.2)."""
    if len(durations) < 2:
        raise InsufficientSampleError("resolution time needs at least two cases")
    seconds = sorted(d.total_seconds() for d in durations)
    p90 = quantiles(seconds, n=10, method="inclusive")[8]
    return ResolutionSummary(
        n=len(seconds), median=timedelta(seconds=median(seconds)), p90=timedelta(seconds=p90)
    )


def csat(scores: Sequence[int]) -> float:
    """Share of 4 and 5 answers on a 1-5 scale."""
    if any(s < 1 or s > 5 for s in scores):
        raise InsufficientSampleError("CSAT scores must be 1-5")
    return rate(sum(s >= 4 for s in scores), len(scores))


def call_cost_paise(outcome: CallOutcome) -> int:
    c = outcome.cost
    return c.telephony + c.stt + c.tts + c.llm + c.whatsapp


def cost_per_resolved_contact_paise(
    outcomes: Sequence[CallOutcome], whatsapp_templates_sent: int
) -> Decimal:
    """All spend (including unresolved calls and every template) over AI-resolved contacts."""
    resolved = sum(o.outcome in AI_RESOLVED for o in outcomes)
    if resolved == 0:
        raise InsufficientSampleError("no AI-resolved contacts")
    total = Decimal(sum(call_cost_paise(o) for o in outcomes))
    total += whatsapp_utility_paise() * whatsapp_templates_sent
    return total / resolved

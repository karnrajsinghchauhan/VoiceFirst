"""The dispatcher: the only caller of telephony.dial (9.3).

Per booking event: ingest -> plan a journey -> queue. Per due queue item:
kill-switch check -> compliance.evaluate (always writes the gate decision) ->
dial in the same transaction -> hand the call to the CallRunner -> record the
outcome, schedule attempt 2 no sooner than the cooldown, send the one
no-answer WhatsApp fallback.

Items are processed strictly one at a time per process (D-201). The attempt
cap and cooldown gates count rows in dial_attempts; with a single writer, no
second clearance can be minted for the same event or number between a gate
evaluation and its dial, so the counts the gates read are exact.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal, Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.campaigns.journeys import JourneyRules, plan_journey
from app.campaigns.models import (
    BookingEventRow,
    CampaignStateRow,
    HoldoutMemberRow,
    QueueItemRow,
    QueueState,
)
from app.compliance.evaluate import evaluate
from app.compliance.killswitch import is_engaged
from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.call_outcome import CallOutcome
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import transaction
from app.core.errors import (
    CooldownError,
    GateError,
    HeldOutError,
    OutsideCallWindowError,
    ProviderError,
)
from app.core.ids import new_id
from app.providers.base import TelephonyProvider
from app.telephony.dial import dial
from app.telephony.handle import CallHandle

Purpose = Literal["J1", "J2"]

# Outcomes after which the customer was never reached; they earn attempt 2 and the fallback.
UNREACHED_OUTCOMES = frozenset({"no_answer", "voicemail"})
# Gates that fail only because of the clock; the item is re-evaluated later instead of blocked.
TIME_BASED_GATE_ERRORS: tuple[type[GateError], ...] = (OutsideCallWindowError, CooldownError)


class CallRunner(Protocol):
    """Runs a placed call to its end (text agent in tests, LiveKit agent in production)."""

    def run(self, handle: CallHandle, event: BookingEvent, purpose: Purpose) -> CallOutcome: ...


class FallbackSender(Protocol):
    """Sends the single no-answer WhatsApp utility template; enforces opt-in and the 1-per-event cap."""

    def send_no_answer_fallback(self, event: BookingEvent) -> None: ...


@dataclass(frozen=True)
class DispatchResult:
    item_id: str
    booking_id: str
    purpose: Purpose
    state: QueueState
    reason: str
    call_id: str | None


class Dispatcher:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        bus: EventBus,
        settings: Settings,
        clock: Clock,
        telephony: TelephonyProvider,
        runner: CallRunner,
        fallback: FallbackSender,
        cli_by_purpose: Mapping[Purpose, str],
        rules: JourneyRules,
    ) -> None:
        self._factory = session_factory
        self._bus = bus
        self._settings = settings
        self._clock = clock
        self._telephony = telephony
        self._runner = runner
        self._fallback = fallback
        self._cli_by_purpose = dict(cli_by_purpose)
        self._rules = rules

    # Ingest

    def ingest(self, payload: Mapping[str, object]) -> BookingEvent:
        """Validates a booking event at the edge, stores it once, and plans its journey.

        Redelivery of an already stored event_id is a no-op, because Kafka delivers at least once.
        """
        event = BookingEvent.model_validate(payload)
        with transaction(self._factory) as session:
            if session.get(BookingEventRow, event.event_id) is not None:
                return event
            now = self._clock.now()
            session.add(
                BookingEventRow(
                    event_id=event.event_id,
                    tenant_id=event.tenant_id,
                    booking_id=event.booking_id,
                    status=event.status,
                    received_at=now,
                    payload=event.model_dump(mode="json"),
                )
            )
            self._supersede_queued(session, event.booking_id)
            plan = plan_journey(event, now, self._rules)
            if plan is not None:
                session.add(
                    QueueItemRow(
                        item_id=new_id("q"),
                        tenant_id=event.tenant_id,
                        booking_event_id=event.event_id,
                        booking_id=event.booking_id,
                        purpose=plan.purpose,
                        cli_e164=self._cli_by_purpose[plan.purpose],
                        due_at=plan.due_at,
                        state="queued",
                        attempts=0,
                        last_reason=None,
                        last_call_id=None,
                        last_outcome=None,
                        last_dialled_at=None,
                        updated_at=now,
                    )
                )
            session.flush()
            self._bus.publish("av.booking-events.v1", event.booking_id, event)
        return event

    def _supersede_queued(self, session: Session, booking_id: str) -> None:
        # A newer event for the booking (paid, cancelled, confirmed) makes any queued call moot.
        session.execute(
            update(QueueItemRow)
            .where(QueueItemRow.booking_id == booking_id, QueueItemRow.state == "queued")
            .values(
                state="dropped",
                last_reason="superseded_by_newer_event",
                updated_at=self._clock.now(),
            )
        )

    # Dispatch

    def run_due(self) -> list[DispatchResult]:
        """Processes every item due now, one at a time. Stops at the kill switch."""
        results: list[DispatchResult] = []
        while True:
            item_id = self._take_next_due()
            if item_id is None:
                return results
            results.append(self._dispatch(item_id))

    def _take_next_due(self) -> str | None:
        with transaction(self._factory) as session:
            tenant = self._settings.tenant_id
            if is_engaged(session, tenant):
                self._drop_all_queued(session, tenant)
                return None
            paused = select(CampaignStateRow.purpose).where(
                CampaignStateRow.tenant_id == tenant, CampaignStateRow.paused.is_(True)
            )
            return session.scalar(
                select(QueueItemRow.item_id)
                .where(
                    QueueItemRow.tenant_id == tenant,
                    QueueItemRow.state == "queued",
                    QueueItemRow.due_at <= self._clock.now(),
                    QueueItemRow.purpose.not_in(paused),
                )
                .order_by(QueueItemRow.due_at, QueueItemRow.item_id)
                .limit(1)
            )

    def _drop_all_queued(self, session: Session, tenant_id: str) -> None:
        session.execute(
            update(QueueItemRow)
            .where(QueueItemRow.tenant_id == tenant_id, QueueItemRow.state == "queued")
            .values(
                state="dropped", last_reason="kill_switch_engaged", updated_at=self._clock.now()
            )
        )

    def _dispatch(self, item_id: str) -> DispatchResult:
        handle, event, result, provider_failure = self._clear_and_dial(item_id)
        if provider_failure is not None:
            raise provider_failure
        if handle is None:
            return result
        outcome = self._runner.run(handle, event, result.purpose)
        return self._record_outcome(item_id, event, handle, outcome)

    def _clear_and_dial(
        self, item_id: str
    ) -> tuple[CallHandle | None, BookingEvent, DispatchResult, ProviderError | None]:
        """One transaction: gate decision, clearance, consumption and dial commit together.

        Gate failures are outcomes of the queue item, so they are recorded rather than raised;
        the gate decision row commits with them. A provider failure is recorded and then raised.
        """
        with transaction(self._factory) as session:
            item = session.get_one(QueueItemRow, item_id)
            event = BookingEvent.model_validate(
                session.get_one(BookingEventRow, item.booking_event_id).payload
            )
            now = self._clock.now()
            item.updated_at = now
            try:
                clearance = evaluate(
                    session,
                    self._bus,
                    self._settings,
                    self._clock,
                    event,
                    item.purpose,
                    item.cli_e164,
                )
            except HeldOutError as exc:
                self._record_holdout(session, event, item)
                return None, event, self._mark(item, "held_out", exc.code), None
            except TIME_BASED_GATE_ERRORS as exc:
                item.due_at = now + self._rules.retry_interval
                return None, event, self._mark(item, "queued", exc.code), None
            except GateError as exc:
                return None, event, self._mark(item, "blocked", exc.code), None
            try:
                with session.begin_nested():
                    handle = dial(
                        session,
                        clearance,
                        self._telephony,
                        self._clock,
                        self._settings.tenant_id,
                        self._settings.phone_pepper,
                    )
            except ProviderError as exc:
                return None, event, self._mark(item, "error", exc.code), exc
            item.attempts += 1
            item.last_call_id = handle.call_id
            item.last_dialled_at = now
            return handle, event, self._mark(item, "in_call", "dialled"), None

    def _record_holdout(self, session: Session, event: BookingEvent, item: QueueItemRow) -> None:
        session.merge(
            HoldoutMemberRow(
                booking_id=event.booking_id,
                tenant_id=event.tenant_id,
                booking_event_id=event.event_id,
                purpose=item.purpose,
                experiment_salt=self._settings.holdout.experiment_salt,
                recorded_at=self._clock.now(),
            )
        )

    def _record_outcome(
        self, item_id: str, event: BookingEvent, handle: CallHandle, outcome: CallOutcome
    ) -> DispatchResult:
        with transaction(self._factory) as session:
            item = session.get_one(QueueItemRow, item_id)
            item.last_outcome = outcome.outcome
            item.updated_at = self._clock.now()
            if outcome.outcome not in UNREACHED_OUTCOMES:
                return self._mark(item, "done", outcome.outcome)
            if item.attempts == 1 and event.customer.whatsapp_opt_in is not None:
                self._fallback.send_no_answer_fallback(event)
            if item.attempts >= self._settings.compliance.max_attempts_per_event:
                return self._mark(item, "done", outcome.outcome)
            assert item.last_dialled_at is not None  # set in the dial transaction
            item.due_at = item.last_dialled_at + timedelta(
                hours=self._settings.compliance.cooldown_hours
            )
            return self._mark(item, "queued", outcome.outcome)

    @staticmethod
    def _mark(item: QueueItemRow, state: QueueState, reason: str) -> DispatchResult:
        item.state = state
        item.last_reason = reason
        return DispatchResult(
            item_id=item.item_id,
            booking_id=item.booking_id,
            purpose=item.purpose,
            state=state,
            reason=reason,
            call_id=item.last_call_id if state == "in_call" else None,
        )

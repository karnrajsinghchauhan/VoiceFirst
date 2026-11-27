"""The production ToolBackend: the agent's allowlisted tools mapped onto the owning modules.

One instance per call. Every tool runs in its own unit of work so that a side effect
(a link sent, an opt-out recorded) is durable the moment the tool returns.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.compliance.consent import mark_dnc
from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import transaction
from app.core.errors import ProviderError
from app.core.ids import mask_booking_id, new_id
from app.core.logging import get_logger
from app.crm.cases import open_case
from app.handoff.models import CallbackRow
from app.handoff.transfer import HumanQueue, attach_ticket, warm_transfer
from app.incidents.service import page_human
from app.messaging import whatsapp
from app.providers.base import CrmProvider, TelephonyProvider, WhatsAppProvider
from app.voice.tools import ToolResult, TransferResult

# [CD] Agoda's app deep link. A plain link, never an offer (D-001).
AGODA_APP_LINK = "https://example.invalid/agoda/app"
CALLBACK_DELAY = timedelta(hours=2)

_log = get_logger(__name__)


class LiveToolBackend:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        bus: EventBus,
        settings: Settings,
        clock: Clock,
        whatsapp_provider: WhatsAppProvider,
        crm: CrmProvider,
        telephony: TelephonyProvider,
        human_queue: HumanQueue,
        provider_call_id: str,
    ) -> None:
        self._factory = session_factory
        self._bus = bus
        self._settings = settings
        self._clock = clock
        self._wa = whatsapp_provider
        self._crm = crm
        self._telephony = telephony
        self._queue = human_queue
        self._provider_call_id = provider_call_id

    def send_payment_link(self, call_id: str, event: BookingEvent) -> ToolResult:
        with transaction(self._factory) as s:
            sent = whatsapp.send_payment_link(s, self._settings, self._clock, self._wa, event)
        return ToolResult(
            "sent", sent.provider_message_id, whatsapp.template_cost_paise(self._settings)
        )

    def send_app_link(self, call_id: str, event: BookingEvent) -> ToolResult:
        with transaction(self._factory) as s:
            sent = whatsapp.send_app_link(
                s, self._settings, self._clock, self._wa, event, AGODA_APP_LINK
            )
        _log.info("customer_initiated_offer_request", extra={"call_id": call_id})
        return ToolResult(
            "sent", sent.provider_message_id, whatsapp.template_cost_paise(self._settings)
        )

    def confirm_details(
        self, call_id: str, event: BookingEvent, details: dict[str, str]
    ) -> ToolResult:
        # The confirmation itself is the call outcome (details_confirmed); nothing to write to
        # Agoda's booking system until that integration exists [CD].
        _log.info("details_confirmed", extra={"call_id": call_id, "fields": sorted(details)})
        return ToolResult("recorded")

    def record_special_request(self, call_id: str, event: BookingEvent, text: str) -> ToolResult:
        # Special requests reach the property through a human case until a property API exists [CD].
        ticket = self._crm.create_ticket(
            subject=f"Special request ({mask_booking_id(event.booking_id)})",
            body=text,
            requester_ref=call_id,
            tags=["agoda_voice", "special_request"],
            priority="normal",
        )
        return ToolResult("recorded", ticket.ticket_id)

    def log_case(
        self, call_id: str, event: BookingEvent, category: str, summary: str
    ) -> ToolResult:
        ticket = self._crm.create_ticket(
            subject=f"Agoda Voice case: {category} ({mask_booking_id(event.booking_id)})",
            body=f"{summary}\nGrievance channel: {self._settings.grievance.channel}",
            requester_ref=call_id,
            tags=["agoda_voice", f"case_{category}"],
            priority="normal",
        )
        return ToolResult("logged", ticket.ticket_id)

    def schedule_callback(
        self, call_id: str, event: BookingEvent, reason: str, when: str
    ) -> ToolResult:
        now = self._clock.now()
        with transaction(self._factory) as s:
            row = CallbackRow(
                callback_id=new_id("cb"),
                tenant_id=self._settings.tenant_id,
                call_id=call_id,
                queue="booker_callback",
                requested_at=now,
                due_at=now + CALLBACK_DELAY,
                reason=f"{reason} (customer said: {when})",
            )
            s.add(row)
        # A promised callback must reach a person: the CRM ticket is what an agent works from.
        ticket = self._crm.create_ticket(
            subject=f"Agoda Voice callback due {row.due_at:%Y-%m-%d %H:%M} UTC ({mask_booking_id(event.booking_id)})",
            body=f"{row.reason}\nGrievance channel: {self._settings.grievance.channel}",
            requester_ref=call_id,
            tags=["agoda_voice", "callback", f"queue_{row.queue}"],
            priority="normal",
        )
        return ToolResult("scheduled", ticket.ticket_id)

    def warm_transfer(
        self, call_id: str, event: BookingEvent, summary: HandoffSummary
    ) -> TransferResult:
        with transaction(self._factory) as s:
            result = warm_transfer(
                s, self._bus, self._queue, self._clock, summary, self._settings.voice_gender
            )
        # The handoff commits before the CRM call: a CRM outage must not erase a transfer that
        # may already have a person on the line. A failed case write pages a human instead.
        try:
            ticket = open_case(self._crm, summary, self._settings.grievance.channel)
        except ProviderError as exc:
            self.alert(call_id, "crm_case_failed", exc.code)
            return TransferResult(
                connected=result.kind == "transferred", queue=summary.queue, ref=result.agent_ref
            )
        with transaction(self._factory) as s:
            attach_ticket(s, summary.call_id, ticket.ticket_id)
        return TransferResult(
            connected=result.kind == "transferred",
            queue=summary.queue,
            ref=result.agent_ref or ticket.ticket_id,
        )

    def mark_dnc(self, call_id: str, event: BookingEvent) -> ToolResult:
        with transaction(self._factory) as s:
            mark_dnc(
                s,
                self._settings,
                phone_e164=event.customer.phone_e164,
                at=self._clock.now(),
                channel="voice",
                call_id=call_id,
            )
        return ToolResult("opted_out")

    def end_call(self, call_id: str, outcome: str) -> ToolResult:
        self._telephony.hang_up(self._provider_call_id)
        return ToolResult("ended")

    def alert(self, call_id: str, code: str, detail: str) -> None:
        with transaction(self._factory) as s:
            page_human(
                s,
                tenant_id=self._settings.tenant_id,
                at=self._clock.now(),
                summary=f"call {call_id}: {code}: {detail}",
            )

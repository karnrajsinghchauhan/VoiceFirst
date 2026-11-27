"""The one way to send WhatsApp (REQ-WA-01..03, REQ-TRAI-08, REQ-PAY-02).

Every send checks, in order: channel not paused; recorded opt-in; template is
utility; per-kind caps. Costs assume every template is paid (REQ-WA-02).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.campaigns.journeys import stay_of
from app.compliance.models import WhatsAppSendRow
from app.contracts.generated.booking_event import BookingEvent
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import (
    FallbackCapError,
    WhatsAppOptInMissingError,
    WhatsAppPausedError,
    WhatsAppTemplateNotAllowedError,
    WhatsAppWindowClosedError,
)
from app.core.ids import new_id, phone_hash, sha256_hex
from app.core.money import format_inr
from app.incidents.service import page_human
from app.messaging.models import InboundMessageRow, WhatsAppStateRow
from app.messaging.templates import TEMPLATES, Template
from app.providers.base import SentMessage, WhatsAppProvider

SendKind = Literal["in_call", "no_answer_fallback", "notice", "survey", "app_link"]


def template_cost_paise(settings: Settings) -> int:
    with_gst = settings.whatsapp_utility_rate_paise * (Decimal(1) + settings.gst_rate)
    return int(with_gst.to_integral_value(rounding=ROUND_CEILING))


def _assert_not_paused(session: Session, tenant_id: str) -> None:
    state = session.get(WhatsAppStateRow, tenant_id)
    if state is not None and state.paused:
        raise WhatsAppPausedError(f"WhatsApp paused: {state.reason}")


def _assert_opted_in(event: BookingEvent) -> None:
    opt_in = event.customer.whatsapp_opt_in
    if opt_in is None:
        raise WhatsAppOptInMissingError("no recorded WhatsApp opt-in for this number")


def _template(name: str) -> Template:
    template = TEMPLATES[name]
    if template.category != "utility":
        raise WhatsAppTemplateNotAllowedError(
            f"{name} is {template.category}; pilot is utility-only"
        )
    return template


def payment_link(settings: Settings, event: BookingEvent) -> str:
    # The link is Agoda-hosted [CD: format]; we only reference the booking opaquely.
    token = sha256_hex(settings.phone_pepper + event.booking_id)[:24]
    return f"{settings.payment_link.base_url}/{token}"


def _send(
    session: Session,
    settings: Settings,
    clock: Clock,
    provider: WhatsAppProvider,
    event: BookingEvent,
    template_name: str,
    params: dict[str, str],
    kind: SendKind,
) -> SentMessage:
    _assert_not_paused(session, event.tenant_id)
    _assert_opted_in(event)
    template = _template(template_name)
    sent = provider.send_template(
        event.customer.phone_e164, template.name, event.customer.preferred_language, params
    )
    session.add(
        WhatsAppSendRow(
            send_id=new_id("wa"),
            tenant_id=event.tenant_id,
            booking_event_id=event.event_id,
            phone_hash=phone_hash(event.customer.phone_e164, settings.phone_pepper),
            template=template.name,
            kind=kind,
            sent_at=clock.now(),
            provider_message_id=sent.provider_message_id,
            cost_paise=template_cost_paise(settings),
        )
    )
    session.flush()
    return sent


def _payment_params(settings: Settings, event: BookingEvent) -> dict[str, str]:
    return {
        "client": settings.client.name,
        "first_name": event.customer.first_name,
        "city": stay_of(event)[0].city,
        "amount": format_inr(event.amount_due.value, event.amount_due.currency),
        "link": payment_link(settings, event),
        "grievance": settings.grievance.channel,
    }


def send_payment_link(
    session: Session,
    settings: Settings,
    clock: Clock,
    provider: WhatsAppProvider,
    event: BookingEvent,
) -> SentMessage:
    """In-call, after the customer's explicit consent to receive the link."""
    return _send(
        session,
        settings,
        clock,
        provider,
        event,
        "av_payment_link_v1",
        _payment_params(settings, event),
        "in_call",
    )


def _fallbacks_sent(session: Session, event_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(WhatsAppSendRow)
        .where(
            WhatsAppSendRow.booking_event_id == event_id,
            WhatsAppSendRow.kind == "no_answer_fallback",
        )
    )
    return session.scalar(stmt) or 0


def send_no_answer_fallback(
    session: Session,
    settings: Settings,
    clock: Clock,
    provider: WhatsAppProvider,
    event: BookingEvent,
) -> SentMessage:
    """J1 no-answer: one utility template per booking_event, only with opt-in (REQ-TRAI-08)."""
    cap = settings.compliance.max_whatsapp_fallbacks_per_event
    if _fallbacks_sent(session, event.event_id) >= cap:
        raise FallbackCapError(f"already sent {cap} WhatsApp fallback(s) for this event")
    return _send(
        session,
        settings,
        clock,
        provider,
        event,
        "av_payment_pending_v1",
        _payment_params(settings, event),
        "no_answer_fallback",
    )


def send_app_link(
    session: Session,
    settings: Settings,
    clock: Clock,
    provider: WhatsAppProvider,
    event: BookingEvent,
    link: str,
) -> SentMessage:
    """D-001: customer-initiated add-on question; a plain app link, no persuasion."""
    return _send(
        session,
        settings,
        clock,
        provider,
        event,
        "av_app_link_v1",
        {"client": settings.client.name, "first_name": event.customer.first_name, "link": link},
        "app_link",
    )


def send_privacy_notice(
    session: Session,
    settings: Settings,
    clock: Clock,
    provider: WhatsAppProvider,
    event: BookingEvent,
) -> SentMessage:
    """REQ-DPDP-01: the itemised notice behind a link."""
    return _send(
        session,
        settings,
        clock,
        provider,
        event,
        "av_privacy_notice_v1",
        {"first_name": event.customer.first_name, "link": settings.grievance.notice_url},
        "notice",
    )


def record_inbound(session: Session, settings: Settings, phone_e164: str, clock: Clock) -> None:
    session.merge(
        InboundMessageRow(
            tenant_id=settings.tenant_id,
            phone_hash=phone_hash(phone_e164, settings.phone_pepper),
            last_inbound_at=clock.now(),
        )
    )
    session.flush()


def send_free_form(
    session: Session,
    settings: Settings,
    clock: Clock,
    provider: WhatsAppProvider,
    phone_e164: str,
    text: str,
    tenant_id: str,
) -> SentMessage:
    """Free-form text only inside the 24 h window opened by the customer's last message."""
    _assert_not_paused(session, tenant_id)
    row = session.get(InboundMessageRow, (tenant_id, phone_hash(phone_e164, settings.phone_pepper)))
    if row is None or clock.now() - row.last_inbound_at >= timedelta(hours=24):
        raise WhatsAppWindowClosedError("outside the 24 h customer-service window")
    return provider.send_text(phone_e164, text)


def poll_quality(
    session: Session, settings: Settings, clock: Clock, provider: WhatsAppProvider
) -> Literal["high", "medium", "low"]:
    """A drop to "low" pauses WhatsApp and pages a human (REQ-WA-03)."""
    rating = provider.quality_rating()
    if rating == "low":
        now = clock.now()
        session.merge(
            WhatsAppStateRow(
                tenant_id=settings.tenant_id,
                paused=True,
                reason="quality rating low",
                changed_at=now,
            )
        )
        page_human(
            session,
            tenant_id=settings.tenant_id,
            at=now,
            severity="sev2",
            summary="WhatsApp quality rating dropped to low; WhatsApp paused",
        )
        session.flush()
    return rating

"""Tables owned by compliance/. Each fact has one owner; other packages read through compliance APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class ConsentRow(Base):
    __tablename__ = "consent_records"
    consent_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    phone_e164: Mapped[str] = mapped_column(String, index=True)
    basis: Mapped[Literal["transaction", "explicit", "inquiry"]] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    booking_id: Mapped[str | None] = mapped_column(String, nullable=True)
    obtained_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    source_ref: Mapped[str] = mapped_column(String)
    consent_manager_id: Mapped[str | None] = mapped_column(String, nullable=True)
    artefact_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    trace_id: Mapped[str] = mapped_column(String)


class CliRow(Base):
    __tablename__ = "cli_registry"
    cli_e164: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    series: Mapped[Literal["140", "1600", "1601"]] = mapped_column(String)
    purpose: Mapped[Literal["service", "transactional", "promotional"]] = mapped_column(String)
    oap: Mapped[str] = mapped_column(String)
    a2p_declared: Mapped[bool] = mapped_column(Boolean)
    declaration_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    dlt_recorded_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[Literal["active", "paused", "retired"]] = mapped_column(String)
    paused_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class PreferenceRow(Base):
    """NCPR / DND state as last synced from the operator registry."""

    __tablename__ = "preference_registry"
    phone_hash: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[Literal["none", "block_promo", "partial", "fully_blocked"]] = mapped_column(
        String
    )
    synced_at: Mapped[datetime] = mapped_column(UtcDateTime)


class OptOutRow(Base):
    __tablename__ = "opt_outs"
    phone_hash: Mapped[str] = mapped_column(String, primary_key=True)
    opted_out_at: Mapped[datetime] = mapped_column(UtcDateTime)
    channel: Mapped[str] = mapped_column(String)
    call_id: Mapped[str | None] = mapped_column(String, nullable=True)


class KillSwitchRow(Base):
    __tablename__ = "kill_switch"
    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    engaged: Mapped[bool] = mapped_column(Boolean)
    actor: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    changed_at: Mapped[datetime] = mapped_column(UtcDateTime)


class GateDecisionRow(Base):
    """Immutable (8.4). Written before any dial."""

    __tablename__ = "gate_decisions"
    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    trace_id: Mapped[str] = mapped_column(String)
    booking_event_id: Mapped[str] = mapped_column(String, index=True)
    booking_id: Mapped[str] = mapped_column(String, index=True)
    purpose: Mapped[str] = mapped_column(String)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    gates: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    clearance_id: Mapped[str | None] = mapped_column(String, nullable=True)


class ClearanceRow(Base):
    __tablename__ = "clearances"
    clearance_id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("gate_decisions.decision_id"))
    tenant_id: Mapped[str] = mapped_column(String)
    booking_event_id: Mapped[str] = mapped_column(String)
    booking_id: Mapped[str] = mapped_column(String)
    phone_e164: Mapped[str] = mapped_column(String)
    cli_e164: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class DialAttemptRow(Base):
    __tablename__ = "dial_attempts"
    attempt_id: Mapped[str] = mapped_column(String, primary_key=True)
    clearance_id: Mapped[str] = mapped_column(ForeignKey("clearances.clearance_id"), unique=True)
    booking_event_id: Mapped[str] = mapped_column(String, index=True)
    booking_id: Mapped[str] = mapped_column(String, index=True)
    phone_hash: Mapped[str] = mapped_column(String)
    cli_e164: Mapped[str] = mapped_column(String)
    dialled_at: Mapped[datetime] = mapped_column(UtcDateTime)
    provider_call_id: Mapped[str] = mapped_column(String)
    call_id: Mapped[str] = mapped_column(String, unique=True)

    __table_args__ = (Index("ix_dial_attempts_phone_time", "phone_hash", "dialled_at"),)


class ComplaintRow(Base):
    __tablename__ = "complaints"
    complaint_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    cli_e164: Mapped[str] = mapped_column(String, index=True)
    complainant_hash: Mapped[str] = mapped_column(String)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime)
    source: Mapped[str] = mapped_column(String)
    ai_flagged: Mapped[bool] = mapped_column(Boolean)
    dlt_ref: Mapped[str | None] = mapped_column(String, nullable=True)


class CampaignPauseRow(Base):
    """All-campaign pause set by the complaint guardrail (REQ-TRAI-06); distinct from the kill switch."""

    __tablename__ = "campaign_pauses"
    pause_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    reason: Mapped[str] = mapped_column(Text)
    paused_at: Mapped[datetime] = mapped_column(UtcDateTime)
    lifted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    lifted_by: Mapped[str | None] = mapped_column(String, nullable=True)


class WhatsAppSendRow(Base):
    __tablename__ = "whatsapp_sends"
    send_id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_event_id: Mapped[str] = mapped_column(String, index=True)
    phone_hash: Mapped[str] = mapped_column(String)
    template: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(
        String
    )  # in_call | no_answer_fallback | notice | survey | app_link
    sent_at: Mapped[datetime] = mapped_column(UtcDateTime)
    provider_message_id: Mapped[str] = mapped_column(String)
    cost_paise: Mapped[int] = mapped_column(Integer)

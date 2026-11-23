"""Implements app.api.ports.CampaignService. A campaign is one journey's queue (J1 or J2)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.ports import CampaignView
from app.campaigns.models import CampaignStateRow, HoldoutMemberRow, QueueItemRow
from app.core.clock import Clock
from app.core.db import transaction
from app.core.errors import NotFoundError
from app.core.types import Purpose

_IDS: dict[str, Purpose] = {"cmp_j1": "J1", "cmp_j2": "J2"}


class CampaignPort:
    def __init__(
        self, session_factory: sessionmaker[Session], tenant_id: str, clock: Clock
    ) -> None:
        self._factory = session_factory
        self._tenant = tenant_id
        self._clock = clock

    def _count(self, session: Session, purpose: Purpose, *states: str) -> int:
        stmt = (
            select(func.count())
            .select_from(QueueItemRow)
            .where(
                QueueItemRow.tenant_id == self._tenant,
                QueueItemRow.purpose == purpose,
                QueueItemRow.state.in_(states),
            )
        )
        return session.scalar(stmt) or 0

    def _view(self, session: Session, campaign_id: str, purpose: Purpose) -> CampaignView:
        state = session.get(CampaignStateRow, (self._tenant, purpose))
        dialled = (
            session.scalar(
                select(func.sum(QueueItemRow.attempts)).where(
                    QueueItemRow.tenant_id == self._tenant, QueueItemRow.purpose == purpose
                )
            )
            or 0
        )
        held = (
            session.scalar(
                select(func.count())
                .select_from(HoldoutMemberRow)
                .where(
                    HoldoutMemberRow.tenant_id == self._tenant, HoldoutMemberRow.purpose == purpose
                )
            )
            or 0
        )
        return CampaignView(
            campaign_id=campaign_id,
            purpose=purpose,
            status="paused" if state is not None and state.paused else "active",
            queued=self._count(session, purpose, "queued"),
            dialled=dialled,
            held_out=held,
        )

    def list_campaigns(self) -> list[CampaignView]:
        with transaction(self._factory) as session:
            return [self._view(session, cid, purpose) for cid, purpose in _IDS.items()]

    def _set(self, campaign_id: str, paused: bool, actor: str, reason: str) -> CampaignView:
        purpose = _IDS.get(campaign_id)
        if purpose is None:
            raise NotFoundError(f"no campaign {campaign_id}")
        with transaction(self._factory) as session:
            session.merge(
                CampaignStateRow(
                    tenant_id=self._tenant,
                    purpose=purpose,
                    paused=paused,
                    actor=actor,
                    reason=reason,
                    changed_at=self._clock.now(),
                )
            )
            session.flush()
            return self._view(session, campaign_id, purpose)

    def pause(self, campaign_id: str, actor: str, reason: str) -> CampaignView:
        return self._set(campaign_id, True, actor, reason)

    def resume(self, campaign_id: str, actor: str, reason: str) -> CampaignView:
        return self._set(campaign_id, False, actor, reason)

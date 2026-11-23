"""Inbound webhooks from WhatsApp (Meta) and telephony (LiveKit). Unauthenticated by bearer
token on purpose: providers cannot hold our tokens. Each delivery is authenticated by its
signature and deduplicated before anything acts on it (S8)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.deps import Db, Deps
from app.core.errors import WebhookSignatureError
from app.core.logging import get_logger
from app.messaging.inbound import handle_inbound
from app.webhooks_in.verify import (
    record_once,
    verify_livekit,
    verify_meta_handshake,
    verify_meta_signature,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_log = get_logger(__name__)


class _Edge(BaseModel):
    # Meta adds fields over time; we read only what we use.
    model_config = ConfigDict(extra="ignore")


class _Text(_Edge):
    body: str


class _Message(_Edge):
    id: str
    timestamp: str
    type: str
    text: _Text | None = None
    sender: str = Field(alias="from")


class _Status(_Edge):
    id: str
    status: str
    timestamp: str


class _Value(_Edge):
    messages: list[_Message] = []
    statuses: list[_Status] = []


class _Change(_Edge):
    field: str
    value: _Value


class _Entry(_Edge):
    changes: list[_Change]


class MetaPayload(_Edge):
    object: str
    entry: list[_Entry]


class Ack(BaseModel):
    accepted: int
    actions: list[Literal["withdrawn", "recorded", "status"]]


def _ts(unix: str) -> datetime:
    return datetime.fromtimestamp(int(unix), UTC)


@router.get("/whatsapp", response_class=PlainTextResponse)
def whatsapp_handshake(
    deps: Deps,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str, Query(alias="hub.challenge")] = "",
) -> str:
    verify_meta_handshake(deps.webhook_secrets.meta_verify_token, mode, token)
    return challenge


@router.post("/whatsapp")
async def whatsapp_inbound(
    request: Request,
    deps: Deps,
    db: Db,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> Ack:
    body = await request.body()
    verify_meta_signature(deps.webhook_secrets.meta_app_secret, body, signature)
    try:
        payload = MetaPayload.model_validate_json(body)
    except ValidationError as exc:
        # Signed by Meta but not a shape we know: refuse loudly rather than guess.
        raise WebhookSignatureError("signed WhatsApp payload has an unknown shape") from exc
    now = deps.clock.now()
    actions: list[Literal["withdrawn", "recorded", "status"]] = []
    for change in (c for e in payload.entry for c in e.changes if c.field == "messages"):
        for msg in change.value.messages:
            record_once(
                db,
                source="whatsapp",
                message_id=msg.id,
                kind="message",
                detail=msg.type,
                sent_at=_ts(msg.timestamp),
                now=now,
            )
            text = msg.text.body if msg.text else ""
            actions.append(
                handle_inbound(
                    db, deps.settings, deps.clock, phone_e164="+" + msg.sender, text=text
                )
            )
        for status in change.value.statuses:
            record_once(
                db,
                source="whatsapp",
                message_id=f"{status.id}:{status.status}",
                kind="status",
                detail=status.status,
                sent_at=_ts(status.timestamp),
                now=now,
            )
            actions.append("status")
    return Ack(accepted=len(actions), actions=actions)


class TelephonyAck(BaseModel):
    event: str


@router.post("/telephony")
async def telephony_inbound(
    request: Request,
    deps: Deps,
    db: Db,
    authorization: Annotated[str | None, Header()] = None,
) -> TelephonyAck:
    body = await request.body()
    secrets = deps.webhook_secrets
    event = verify_livekit(secrets.livekit_api_key, secrets.livekit_api_secret, body, authorization)
    record_once(
        db,
        source="telephony",
        message_id=event.id,
        kind=event.event,
        detail=f"room={event.room.name}",
        sent_at=datetime.fromtimestamp(event.created_at, UTC),
        now=deps.clock.now(),
    )
    _log.info("telephony webhook", extra={"event": event.event, "room": event.room.name})
    return TelephonyAck(event=event.event)

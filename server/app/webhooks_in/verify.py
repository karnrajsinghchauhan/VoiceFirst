"""Inbound webhook authentication and replay protection.

Every inbound delivery must pass both checks before anything acts on it:
1. Signature: Meta signs the raw body with HMAC-SHA256 under the app secret
   (X-Hub-Signature-256: sha256=<hex>); LiveKit sends a JWT whose sha256 claim is the
   body hash, signed with the API secret.
2. Replay: the message id has not been seen, and its timestamp is within the window.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta

from livekit import api as lk
from sqlalchemy.orm import Session

from app.core.errors import WebhookReplayError, WebhookSignatureError
from app.webhooks_in.models import WebhookReceiptRow, WebhookSource

# Long enough for provider retries after a brief outage of ours, short enough that a
# captured request cannot be replayed hours later.
REPLAY_WINDOW = timedelta(minutes=10)


@dataclass(frozen=True)
class WebhookSecrets:
    meta_app_secret: str
    meta_verify_token: str
    livekit_api_key: str
    livekit_api_secret: str


def verify_meta_signature(app_secret: str, body: bytes, header: str | None) -> None:
    if not app_secret:
        raise WebhookSignatureError("WhatsApp app secret is not configured")
    if header is None or not header.startswith("sha256="):
        raise WebhookSignatureError("missing or malformed X-Hub-Signature-256")
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, header.removeprefix("sha256=")):
        raise WebhookSignatureError("WhatsApp signature does not match the body")


def verify_meta_handshake(verify_token: str, mode: str | None, token: str | None) -> None:
    if not verify_token or mode != "subscribe" or token is None:
        raise WebhookSignatureError("invalid WhatsApp webhook handshake")
    if not hmac.compare_digest(verify_token, token):
        raise WebhookSignatureError("WhatsApp verify token does not match")


def verify_livekit(
    api_key: str, api_secret: str, body: bytes, auth_header: str | None
) -> lk.WebhookEvent:
    """Returns the parsed LiveKit WebhookEvent; raises on any signature problem."""
    if not api_key or not api_secret:
        raise WebhookSignatureError("LiveKit webhook secret is not configured")
    if not auth_header:
        raise WebhookSignatureError("missing Authorization header on LiveKit webhook")
    receiver = lk.WebhookReceiver(lk.TokenVerifier(api_key, api_secret))
    try:
        return receiver.receive(body.decode(), auth_header.removeprefix("Bearer "))
    except Exception as exc:  # the receiver raises several unrelated types for bad input
        raise WebhookSignatureError("LiveKit webhook signature invalid") from exc


def record_once(
    session: Session,
    *,
    source: WebhookSource,
    message_id: str,
    kind: str,
    detail: str,
    sent_at: datetime,
    now: datetime,
) -> None:
    """Stores the receipt or raises WebhookReplayError. Call after the signature check."""
    if abs(now - sent_at) > REPLAY_WINDOW:
        raise WebhookReplayError(f"{source} delivery {message_id} is outside the replay window")
    if session.get(WebhookReceiptRow, (source, message_id)) is not None:
        raise WebhookReplayError(f"{source} delivery {message_id} was already processed")
    session.add(
        WebhookReceiptRow(
            source=source,
            message_id=message_id,
            kind=kind,
            detail=detail,
            sent_at=sent_at,
            received_at=now,
        )
    )
    session.flush()

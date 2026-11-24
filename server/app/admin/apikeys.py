"""API keys: scoped, rotatable, hashed at rest, with last-used time (brief v3 S7).

Token format `avk_<key_id>_<secret>`. Only sha256(secret) is stored: the secret is 32 random
bytes, so a fast hash is enough (there is nothing to brute-force). The token is shown once.
"""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.admin.rbac import Permission, Principal, principal_for
from app.core.db import Base, UtcDateTime
from app.core.errors import AuthError, NotFoundError, StateConflictError
from app.core.ids import sha256_hex

PREFIX = "avk_"


class ApiKeyRow(Base):
    __tablename__ = "api_keys"
    key_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    secret_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[str] = mapped_column(String)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String, nullable=True)


@dataclass(frozen=True)
class IssuedKey:
    key_id: str
    token: str  # shown once; never stored


def issue(
    session: Session,
    *,
    tenant_id: str,
    name: str,
    role: str,
    scopes: frozenset[Permission] | None,
    created_by: str,
    now: datetime,
    ttl: timedelta | None,
) -> IssuedKey:
    principal_for("check", role, scopes)  # rejects unknown roles and scopes beyond the role
    key_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(32)
    session.add(
        ApiKeyRow(
            key_id=key_id,
            tenant_id=tenant_id,
            name=name,
            role=role,
            scopes=sorted(scopes) if scopes is not None else None,
            secret_hash=sha256_hex(secret),
            created_at=now,
            created_by=created_by,
            expires_at=now + ttl if ttl else None,
            last_used_at=None,
            revoked_at=None,
            replaced_by=None,
        )
    )
    session.flush()
    return IssuedKey(key_id=key_id, token=f"{PREFIX}{key_id}_{secret}")


def _scopes(row: ApiKeyRow) -> frozenset[Permission] | None:
    # Scopes were validated against Permission when the key was issued.
    return cast("frozenset[Permission]", frozenset(row.scopes)) if row.scopes is not None else None


def _get(session: Session, key_id: str) -> ApiKeyRow:
    row = session.get(ApiKeyRow, key_id)
    if row is None:
        raise NotFoundError(f"no API key {key_id}")
    return row


def revoke(session: Session, key_id: str, now: datetime) -> None:
    row = _get(session, key_id)
    if row.revoked_at is not None:
        raise StateConflictError(f"API key {key_id} is already revoked")
    row.revoked_at = now
    session.flush()


def rotate(session: Session, key_id: str, *, created_by: str, now: datetime) -> IssuedKey:
    """A new secret with the same name, role and scopes; the old key stops working now."""
    old = _get(session, key_id)
    if old.revoked_at is not None:
        raise StateConflictError(f"API key {key_id} is revoked; issue a new one")
    ttl = old.expires_at - old.created_at if old.expires_at else None
    new = issue(
        session,
        tenant_id=old.tenant_id,
        name=old.name,
        role=old.role,
        scopes=_scopes(old),
        created_by=created_by,
        now=now,
        ttl=ttl,
    )
    old.revoked_at = now
    old.replaced_by = new.key_id
    session.flush()
    return new


def authenticate(session: Session, token: str, now: datetime) -> Principal:
    body = token.removeprefix(PREFIX)
    key_id, sep, secret = body.partition("_")
    if not sep:
        raise AuthError("malformed API key")
    row = session.get(ApiKeyRow, key_id)
    # Compare against a hash either way so an unknown key id costs the same as a wrong secret.
    expected = row.secret_hash if row is not None else sha256_hex("")
    if not hmac.compare_digest(expected, sha256_hex(secret)) or row is None:
        raise AuthError("unknown API key")
    if row.revoked_at is not None:
        raise AuthError("API key revoked")
    if row.expires_at is not None and now >= row.expires_at:
        raise AuthError("API key expired")
    row.last_used_at = now
    session.flush()
    return principal_for(f"key:{row.name}:{row.key_id}", row.role, _scopes(row))


def list_keys(session: Session, tenant_id: str) -> list[ApiKeyRow]:
    return list(
        session.scalars(
            select(ApiKeyRow).where(ApiKeyRow.tenant_id == tenant_id).order_by(ApiKeyRow.created_at)
        )
    )

"""RBAC (2.7 baseline: least privilege). Roles map to an explicit permission set; nothing is implied."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Literal

from app.core.errors import AuthError, ForbiddenError
from app.core.ids import sha256_hex

Role = Literal["admin", "ops", "auditor", "read_only"]
Permission = Literal[
    "campaigns:read",
    "campaigns:write",
    "calls:read",
    "transcripts:read",
    "consent:read",
    "consent:write",
    "cli:read",
    "cli:write",
    "handoff:read",
    "handoff:write",
    "killswitch:read",
    "killswitch:write",
    "metrics:read",
    "simulate:run",
    "rights:read",
    "rights:write",
    "incidents:read",
    "incidents:write",
    "audit:read",
    "apikeys:write",
]

_READ_ONLY: frozenset[Permission] = frozenset(
    {
        "campaigns:read",
        "calls:read",
        "cli:read",
        "handoff:read",
        "killswitch:read",
        "metrics:read",
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    "read_only": _READ_ONLY,
    # Auditors see evidence (consent, transcripts, audit, rights) but change nothing.
    "auditor": _READ_ONLY
    | {"consent:read", "transcripts:read", "rights:read", "incidents:read", "audit:read"},
    # Ops run the floor: pause, kill, hand off, simulate. They cannot change CLIs or consent.
    "ops": _READ_ONLY
    | {
        "campaigns:write",
        "handoff:write",
        "killswitch:write",
        "simulate:run",
        "incidents:read",
        "incidents:write",
    },
    "admin": _READ_ONLY
    | {
        "campaigns:write",
        "transcripts:read",
        "consent:read",
        "consent:write",
        "cli:write",
        "handoff:write",
        "killswitch:write",
        "simulate:run",
        "rights:read",
        "rights:write",
        "incidents:read",
        "incidents:write",
        "audit:read",
        "apikeys:write",
    },
}


@dataclass(frozen=True)
class Principal:
    actor: str
    role: Role
    # Effective permissions: the role's set, narrowed by an API key's scopes.
    permissions: frozenset[Permission]


def principal_for(actor: str, role: str, scopes: frozenset[Permission] | None = None) -> Principal:
    if role not in ROLE_PERMISSIONS:
        raise AuthError(f"credential mapped to unknown role {role!r}")
    granted = ROLE_PERMISSIONS[role]  # type: ignore[index]
    if scopes is not None and not scopes <= granted:
        raise AuthError("API key scopes exceed its role")
    return Principal(
        actor=actor,
        role=role,  # type: ignore[arg-type]
        permissions=granted if scopes is None else scopes,
    )


def resolve_token(api_tokens: dict[str, str], token: str) -> Principal:
    for known, role in api_tokens.items():
        # Constant-time compare so token prefixes cannot be guessed by timing.
        if hmac.compare_digest(known.encode(), token.encode()):
            return principal_for(f"{role}:{sha256_hex(token)[:8]}", role)
    raise AuthError("unknown API token")


def authorize(principal: Principal, permission: Permission) -> None:
    if permission not in principal.permissions:
        raise ForbiddenError(f"{principal.actor} ({principal.role}) lacks {permission}")

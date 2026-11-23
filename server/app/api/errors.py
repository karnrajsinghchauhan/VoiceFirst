"""The one place typed errors become HTTP statuses."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.errors import (
    AgodaVoiceError,
    AuthError,
    ConfigError,
    ForbiddenError,
    GateError,
    NotFoundError,
    ProviderError,
    StateConflictError,
)
from app.core.redaction import redact_text

# Ordered most specific first; the first isinstance match wins. 422 stays FastAPI's own
# request-validation response so the two error shapes never share a status.
_STATUS: tuple[tuple[type[AgodaVoiceError], int], ...] = (
    (AuthError, 401),
    (ForbiddenError, 403),
    (NotFoundError, 404),
    (StateConflictError, 409),
    (GateError, 409),
    (ProviderError, 502),
    (ConfigError, 500),
    (AgodaVoiceError, 400),
)


class ErrorBody(BaseModel):
    error: str
    detail: str


# Documented on every operation so clients (and schemathesis) know the error shape.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorBody} for status in sorted({s for _, s in _STATUS})
}


def status_for(exc: AgodaVoiceError) -> int:
    for cls, status in _STATUS:
        if isinstance(exc, cls):
            return status
    raise AssertionError("AgodaVoiceError is the last entry")  # unreachable by construction


async def handle_agoda_voice_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AgodaVoiceError)
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthError) else None
    return JSONResponse(
        status_code=status_for(exc),
        content={"error": exc.code, "detail": redact_text(str(exc))},
        headers=headers,
    )

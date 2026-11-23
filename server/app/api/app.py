"""FastAPI app factory. Every dependency is passed in; nothing is built from globals."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.routing import Match

from app.api.deps import ApiDeps
from app.api.errors import ERROR_RESPONSES, handle_agoda_voice_error
from app.api.routes import ops, records, rights
from app.core.errors import AgodaVoiceError

DISCLAIMER = (
    "Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by "
    "Agoda."
)


def _route_label(request: Request) -> str:
    # The route template, not the raw path, so call ids do not explode metric cardinality.
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return str(getattr(route, "path", "unknown"))
    return "unmatched"


def create_app(deps: ApiDeps) -> FastAPI:
    app = FastAPI(
        title="Agoda Voice API",
        version="1.0.0",
        description=DISCLAIMER,
        responses=ERROR_RESPONSES,
    )
    app.state.deps = deps
    app.add_exception_handler(AgodaVoiceError, handle_agoda_voice_error)

    @app.middleware("http")
    async def count_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        deps.metrics.requests.labels(_route_label(request), str(response.status_code)).inc()
        return response

    app.include_router(ops.router)
    app.include_router(records.router)
    app.include_router(rights.router)
    return app

"""FastAPI app factory. Every dependency is passed in; nothing is built from globals."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from app.api.deps import ApiDeps
from app.api.errors import ERROR_RESPONSES, handle_agoda_voice_error, handle_http_error
from app.api.routes import admin, demo, ops, records, rights, status
from app.core.errors import AgodaVoiceError

DISCLAIMER = (
    "Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by "
    "Agoda."
)


def _route_label(request: Request) -> str:
    # The route template, not the raw path, so call ids do not explode metric cardinality.
    # The router records the matched route in the scope; absent means nothing matched (404).
    route = request.scope.get("route")
    if route is None:
        return "unmatched"
    return str(route.path)


def create_app(deps: ApiDeps) -> FastAPI:
    app = FastAPI(
        title="Agoda Voice API",
        version="1.0.0",
        description=DISCLAIMER,
        responses=ERROR_RESPONSES,
    )
    app.state.deps = deps
    app.add_exception_handler(AgodaVoiceError, handle_agoda_voice_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)

    @app.middleware("http")
    async def count_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        deps.metrics.requests.labels(_route_label(request), str(response.status_code)).inc()
        return response

    @app.middleware("http")
    async def complete_allow_header(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Starlette answers 405 from the first route matching the path, so a path served by
        # separate GET and POST routes would advertise only one method. List all of them.
        response = await call_next(request)
        if response.status_code == 405:
            methods: set[str] = set()
            for route in app.router.routes:
                match, _ = route.matches(request.scope)
                if match != Match.NONE and isinstance(route, APIRoute) and route.methods:
                    methods |= route.methods
            response.headers["Allow"] = ", ".join(sorted(methods))
        return response

    app.include_router(ops.router)
    app.include_router(admin.router)
    app.include_router(records.router)
    app.include_router(rights.router)
    app.include_router(demo.router)
    app.include_router(status.router)
    return app

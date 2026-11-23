from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.deps import ApiDeps
from app.api.stubs import build_stub_deps

ADMIN = {"Authorization": "Bearer dev-admin-token"}
OPS = {"Authorization": "Bearer dev-ops-token"}
AUDITOR = {"Authorization": "Bearer dev-auditor-token"}
RO = {"Authorization": "Bearer dev-ro-token"}


@pytest.fixture
def deps(settings, session_factory, bus, clock) -> ApiDeps:
    return build_stub_deps(settings, session_factory, bus, clock)


@pytest.fixture
def app(deps) -> FastAPI:
    return create_app(deps)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)

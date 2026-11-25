"""L2: OpenAPI conformance. Every documented operation, fuzzed, never returns a 5xx, matches its
schema, and rejects requests whose auth is stripped or invalid."""

from __future__ import annotations

import pytest
import schemathesis
from hypothesis import HealthCheck, settings

# FastAPI emits OpenAPI 3.1, which schemathesis 3.x supports behind a flag.
schemathesis.experimental.OPEN_API_3_1.enable()
schema = schemathesis.from_pytest_fixture("api_schema")


@schemathesis.auth()
class AdminToken:
    """Registered auth so schemathesis can also verify that missing auth is refused."""

    def get(self, case, context):
        return "dev-admin-token"

    def set(self, case, data, context):
        case.headers = {**(case.headers or {}), "Authorization": f"Bearer {data}"}


@pytest.fixture
def api_schema(app):
    return schemathesis.from_asgi("/openapi.json", app)


@schema.parametrize()
@settings(max_examples=15, deadline=None, suppress_health_check=list(HealthCheck))
def test_api_conforms(case):
    case.call_and_validate()

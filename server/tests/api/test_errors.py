import pytest

from app.api.errors import status_for
from app.core import errors as e


@pytest.mark.parametrize(
    ("exc", "status"),
    [
        (e.AuthError("x"), 401),
        (e.ForbiddenError("x"), 403),
        (e.NotFoundError("x"), 404),
        (e.StateConflictError("x"), 409),
        (e.KillSwitchEngagedError("x"), 409),
        (e.ProviderTimeoutError("x"), 502),
        (e.ProductionConfigError("x"), 500),
        (e.ToolNotAllowedError("x"), 400),
    ],
)
def test_status_mapping(exc, status):
    assert status_for(exc) == status

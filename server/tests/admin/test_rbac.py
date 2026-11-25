import pytest

from app.admin.rbac import ROLE_PERMISSIONS, Principal, authorize, resolve_token
from app.core.errors import AuthError, ForbiddenError

TOKENS = {"t-admin": "admin", "t-ops": "ops", "t-aud": "auditor", "t-ro": "read_only"}


def test_resolve_token_and_actor_hides_token():
    p = resolve_token(TOKENS, "t-ops")
    assert p.role == "ops" and "t-ops" not in p.actor


def test_unknown_token():
    with pytest.raises(AuthError):
        resolve_token(TOKENS, "nope")


def test_token_with_unknown_role():
    with pytest.raises(AuthError):
        resolve_token({"t": "root"}, "t")


def test_least_privilege_matrix():
    writes = {p for perms in ROLE_PERMISSIONS.values() for p in perms if p.endswith(":write")}
    assert not {p for p in ROLE_PERMISSIONS["read_only"] if p.endswith(":write")}
    assert not {p for p in ROLE_PERMISSIONS["auditor"] if p.endswith(":write")}
    assert "cli:write" not in ROLE_PERMISSIONS["ops"]
    assert "consent:write" not in ROLE_PERMISSIONS["ops"]
    assert "transcripts:read" not in ROLE_PERMISSIONS["read_only"]
    assert "killswitch:write" in ROLE_PERMISSIONS["ops"]
    assert writes <= ROLE_PERMISSIONS["admin"]
    # Every role is a superset of read-only.
    for perms in ROLE_PERMISSIONS.values():
        assert ROLE_PERMISSIONS["read_only"] <= perms


def test_authorize_raises_forbidden():
    with pytest.raises(ForbiddenError):
        authorize(Principal("ro:x", "read_only"), "killswitch:write")
    authorize(Principal("ops:x", "ops"), "killswitch:write")

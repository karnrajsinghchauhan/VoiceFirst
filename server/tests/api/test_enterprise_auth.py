"""S7: scoped, rotatable, hashed API keys; OIDC SSO; audit export."""

from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import replace
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.admin import apikeys
from app.admin.oidc import OidcVerifier
from app.core.config import OidcSettings
from app.core.errors import AuthError

ADMIN = {"Authorization": "Bearer dev-admin-token"}
REASON = "procurement test"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_key_is_hashed_at_rest_and_shown_once(client, session_factory):
    r = client.post(
        "/api-keys", json={"name": "crm-sync", "role": "read_only", "reason": REASON}, headers=ADMIN
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    with session_factory() as s:
        row = s.get(apikeys.ApiKeyRow, r.json()["key_id"])
        assert row is not None and token.split("_", 2)[2] not in row.secret_hash
    listed = client.get("/api-keys", headers=ADMIN).json()
    assert "token" not in listed[0] and listed[0]["last_used_at"] is None
    assert client.get("/campaigns", headers=_bearer(token)).status_code == 200
    assert client.get("/api-keys", headers=ADMIN).json()[0]["last_used_at"] is not None


def test_scopes_narrow_the_role(client):
    token = client.post(
        "/api-keys",
        json={"name": "metrics-only", "role": "ops", "scopes": ["metrics:read"], "reason": REASON},
        headers=ADMIN,
    ).json()["token"]
    assert client.get("/metrics", headers=_bearer(token)).status_code == 200
    assert client.get("/campaigns", headers=_bearer(token)).status_code == 403
    r = client.post("/killswitch", json={"engaged": True, "reason": "nope"}, headers=_bearer(token))
    assert r.status_code == 403


def test_scopes_beyond_the_role_are_refused(client):
    r = client.post(
        "/api-keys",
        json={
            "name": "sneaky",
            "role": "read_only",
            "scopes": ["killswitch:write"],
            "reason": REASON,
        },
        headers=ADMIN,
    )
    assert r.status_code == 401


def test_rotation_revokes_the_old_key(client):
    issued = client.post(
        "/api-keys", json={"name": "rot", "role": "read_only", "reason": REASON}, headers=ADMIN
    ).json()
    new = client.post(
        f"/api-keys/{issued['key_id']}/rotate", json={"reason": REASON}, headers=ADMIN
    ).json()
    assert client.get("/campaigns", headers=_bearer(issued["token"])).status_code == 401
    assert client.get("/campaigns", headers=_bearer(new["token"])).status_code == 200


def test_revoked_and_expired_keys_fail(session_factory, settings, clock):
    with session_factory() as s:
        key = apikeys.issue(
            s,
            tenant_id=settings.tenant_id,
            name="exp",
            role="read_only",
            scopes=None,
            created_by="t",
            now=clock.now(),
            ttl=timedelta(days=1),
        )
        apikeys.authenticate(s, key.token, clock.now())
        with pytest.raises(AuthError, match="expired"):
            apikeys.authenticate(s, key.token, clock.now() + timedelta(days=1))
        apikeys.revoke(s, key.key_id, clock.now())
        with pytest.raises(AuthError, match="revoked"):
            apikeys.authenticate(s, key.token, clock.now())
        with pytest.raises(AuthError):
            apikeys.authenticate(s, key.token[:-2] + "xx", clock.now())


def test_key_actions_are_audited_and_export_works(client):
    client.post(
        "/api-keys", json={"name": "audited", "role": "read_only", "reason": REASON}, headers=ADMIN
    )
    as_json = client.get("/audit/export?format=json", headers=ADMIN)
    assert as_json.status_code == 200
    actions = [r["action"] for r in json.loads(as_json.text)]
    assert "api_key.issue" in actions
    as_csv = client.get("/audit/export?format=csv", headers=ADMIN)
    rows = list(csv.DictReader(io.StringIO(as_csv.text)))
    assert {"api_key.issue", "audit.export"} <= {r["action"] for r in rows}
    ro = client.get("/audit/export", headers={"Authorization": "Bearer dev-ro-token"})
    assert ro.status_code == 403


# OIDC: a locally generated RSA key stands in for the identity provider's JWKS.
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_KEY.public_key())) | {
    "kid": "k1",
    "alg": "RS256",
}
_OIDC = OidcSettings(
    issuer="https://idp.example.invalid",
    audience="av-console",
    jwks_url="https://idp.example.invalid/jwks",
    group_roles={"av-admins": "admin", "av-auditors": "auditor"},
)


def _id_token(**claims: object) -> str:
    now = int(time.time())
    body = {
        "iss": _OIDC.issuer,
        "aud": _OIDC.audience,
        "sub": "karn",
        "iat": now,
        "exp": now + 300,
        "groups": ["av-auditors"],
    } | claims
    return jwt.encode(body, _KEY, algorithm="RS256", headers={"kid": "k1"})


@pytest.fixture
def sso_client(deps):
    from fastapi.testclient import TestClient

    from app.api.app import create_app

    return TestClient(create_app(replace(deps, oidc=OidcVerifier(_OIDC, {"keys": [_JWK]}))))


def test_sso_token_maps_group_to_role(sso_client):
    who = sso_client.get("/whoami", headers=_bearer(_id_token())).json()
    assert who == {"actor": "sso:karn", "role": "auditor"}
    admin = sso_client.get(
        "/whoami", headers=_bearer(_id_token(groups=["av-admins", "av-auditors"]))
    )
    assert admin.json()["role"] == "admin"


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.invalid"},
        {"exp": int(time.time()) - 600},
        {"groups": ["staff"]},
    ],
)
def test_bad_sso_tokens_are_refused(sso_client, claims):
    assert sso_client.get("/whoami", headers=_bearer(_id_token(**claims))).status_code == 401


def test_token_signed_by_another_key_is_refused(sso_client):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(
        {
            "iss": _OIDC.issuer,
            "aud": _OIDC.audience,
            "sub": "x",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "groups": ["av-admins"],
        },
        other,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    assert sso_client.get("/whoami", headers=_bearer(forged)).status_code == 401


def test_sso_not_configured_refuses_jwts(client):
    assert client.get("/whoami", headers=_bearer(_id_token())).status_code == 401

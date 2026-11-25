"""OIDC SSO for the console (brief v3 S7). SAML-ready: a SAML assertion would map to the
same Principal through the same group-to-role table; no SAML code exists yet.

The console's OIDC client (code flow + PKCE) obtains an ID token; the API verifies it here:
RS256 signature against the issuer's JWKS, issuer, audience, expiry. The role comes from
one claim (default `groups`) through an explicit table; a user in no mapped group is refused.
"""

from __future__ import annotations

from typing import Any

import httpx
import jwt

from app.admin.rbac import Principal, Role, principal_for
from app.core.config import OidcSettings
from app.core.errors import AuthError, ProviderError

# When a user is in several mapped groups the most privileged role wins, in this order.
_PRECEDENCE: tuple[Role, ...] = ("admin", "ops", "auditor", "read_only")


def fetch_jwks(url: str) -> dict[str, Any]:
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderError(f"JWKS fetch failed: {exc}") from exc
    body = response.json()
    if not isinstance(body, dict) or "keys" not in body:
        raise ProviderError("JWKS response has no keys")
    return body


class OidcVerifier:
    def __init__(self, settings: OidcSettings, jwks: dict[str, Any]) -> None:
        self._s = settings
        self._keys = {k["kid"]: jwt.PyJWK(k) for k in jwks["keys"] if "kid" in k}
        if not self._keys:
            raise AuthError("JWKS has no usable keys")

    def verify(self, id_token: str) -> Principal:
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
        except jwt.PyJWTError as exc:
            raise AuthError(f"malformed ID token: {exc}") from exc
        key = self._keys.get(kid)
        if key is None:
            raise AuthError("ID token signed by an unknown key")
        try:
            claims = jwt.decode(
                id_token,
                key=key,
                algorithms=["RS256"],
                audience=self._s.audience,
                issuer=self._s.issuer,
                leeway=self._s.leeway_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthError(f"ID token rejected: {exc}") from exc
        groups = claims.get(self._s.role_claim, [])
        roles = {self._s.group_roles[g] for g in groups if g in self._s.group_roles}
        role = next((r for r in _PRECEDENCE if r in roles), None)
        if role is None:
            raise AuthError("user is in no group mapped to a console role")
        return principal_for(f"sso:{claims['sub']}", role)

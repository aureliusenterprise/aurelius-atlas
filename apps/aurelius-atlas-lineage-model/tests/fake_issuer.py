"""The fake Keycloak issuer the app's auth verifier talks to in tests.

Its own module, not the conftest: the trace check collects ``tests/`` and
``e2e/`` in one run, and same-named ``conftest`` modules collide — helpers
import by a unique name (the 8.2 fake upstream in this directory sets the
pattern). The conftest's fixtures and the app tests both import from here.
"""

# ruff: noqa: INP001
from __future__ import annotations

import json
import time
from typing import Any

import httpx2 as httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

ISSUER = "http://issuer.test"
REALM = "master"
BASE_URL = f"{ISSUER}/realms/{REALM}"
KID = "test-key"
AUDIENCE = "aurelius-atlas-lineage-model"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()


def _jwk() -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = KID
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return jwk


def issuer_client() -> httpx.Client:
    """An HTTP client answering discovery and JWKS like Keycloak."""
    jwk = _jwk()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json={"jwks_uri": f"{BASE_URL}/protocol/openid-connect/certs"})
        if request.url.path.endswith("/certs"):
            return httpx.Response(200, json={"keys": [jwk]})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def make_token(
    *,
    audience: str | list[str] | None = AUDIENCE,
    azp: str | None = AUDIENCE,
    issuer: str = BASE_URL,
    expires_in: int = 60,
) -> str:
    """Mint an RS256 token as the fake issuer would, with the given claims."""
    now = int(time.time())
    claims: dict[str, Any] = {"iss": issuer, "iat": now, "exp": now + expires_in, "sub": "user-1", "nbf": now - 1}
    if audience is not None:
        claims["aud"] = audience
    if azp is not None:
        claims["azp"] = azp
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})

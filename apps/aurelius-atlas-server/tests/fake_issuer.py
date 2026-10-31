"""A fake identity provider: Keycloak's discovery, keys and token endpoint, and the tokens it signs (AUT-02).

The server's verifier and sign-in client talk to it through mock transports, so no test reaches a network.
"""

# ruff: noqa: INP001

import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs

import httpx2 as httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

SERVER_URL = "https://keycloak.test"
REALM = "master"
ISSUER = f"{SERVER_URL}/realms/{REALM}"
CLIENT_ID = "aurelius-atlas-server"
CLIENT_SECRET = "test-client-secret"  # noqa: S105 - the fake provider's own
WEBAPP = "aurelius"
KID = "test-key"
TOKEN_ENDPOINT = f"{ISSUER}/protocol/openid-connect/token"
AUTHORIZATION_ENDPOINT = f"{ISSUER}/protocol/openid-connect/auth"
END_SESSION_ENDPOINT = f"{ISSUER}/protocol/openid-connect/logout"

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class FakeIssuer:
    """The provider: it signs tokens, answers discovery and keys, and grants codes and refresh tokens it issued.

    ``codes`` maps a code to the nonce and user it signs in; ``lifetime`` is how long its access tokens last.
    """

    codes: dict[str, tuple[str, str]] = field(default_factory=dict)
    refresh_tokens: dict[str, str] = field(default_factory=dict)
    lifetime: int = 300
    grants: list[str] = field(default_factory=list)

    def token(  # noqa: PLR0913 - the claims a test shapes
        self,
        user: str = "admin",
        *,
        azp: str = WEBAPP,
        issuer: str = ISSUER,
        expires_in: int | None = None,
        roles: list[str] | None = None,
        key: rsa.RSAPrivateKey | None = None,
        **claims: Any,  # noqa: ANN401 - further claims
    ) -> str:
        """An access token of the user, as the provider signs it."""
        now = int(time.time())
        body = {
            "iss": issuer,
            "sub": f"id-{user}",
            "azp": azp,
            "iat": now,
            "exp": now + (self.lifetime if expires_in is None else expires_in),
            "preferred_username": user,
            "realm_access": {"roles": roles if roles is not None else ["default-roles-master"]},
            **claims,
        }
        return jwt.encode(body, key if key is not None else _KEY, algorithm="RS256", headers={"kid": KID})

    def grant_code(self, nonce: str, user: str = "admin") -> str:
        """A code the token endpoint exchanges for the user's tokens, the ID token with the nonce."""
        code = secrets.token_urlsafe(8)
        self.codes[code] = (nonce, user)
        return code

    def sync_client(self) -> httpx.Client:
        """The verifier's client: discovery and keys."""
        return httpx.Client(transport=httpx.MockTransport(self._documents))

    def async_client(self) -> httpx.AsyncClient:
        """The sign-in client's client: the token endpoint."""
        return httpx.AsyncClient(transport=httpx.MockTransport(self._token_endpoint))

    def _documents(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
                    "authorization_endpoint": AUTHORIZATION_ENDPOINT,
                    "token_endpoint": TOKEN_ENDPOINT,
                    "end_session_endpoint": END_SESSION_ENDPOINT,
                },
            )
        if request.url.path.endswith("/certs"):
            jwk = json.loads(RSAAlgorithm.to_jwk(_KEY.public_key()))
            return httpx.Response(200, json={"keys": [{**jwk, "kid": KID, "alg": "RS256", "use": "sig"}]})
        return httpx.Response(404)

    def _token_endpoint(self, request: httpx.Request) -> httpx.Response:
        form = {name: values[0] for name, values in parse_qs(request.content.decode()).items()}
        self.grants.append(form.get("grant_type", ""))
        if form.get("client_id") != CLIENT_ID or form.get("client_secret") != CLIENT_SECRET:
            return httpx.Response(401, json={"error": "unauthorized_client"})
        if form.get("grant_type") == "authorization_code" and form.get("code") in self.codes:
            nonce, user = self.codes.pop(form["code"])
            return self._tokens(user, nonce)
        if form.get("grant_type") == "refresh_token" and form.get("refresh_token") in self.refresh_tokens:
            return self._tokens(self.refresh_tokens.pop(form["refresh_token"]), None)
        return httpx.Response(400, json={"error": "invalid_grant"})

    def _tokens(self, user: str, nonce: str | None) -> httpx.Response:
        refresh = secrets.token_urlsafe(8)
        self.refresh_tokens[refresh] = user
        body = {
            "access_token": self.token(user, azp=CLIENT_ID),
            "expires_in": self.lifetime,
            "refresh_token": refresh,
        }
        if nonce is not None:
            body["id_token"] = self.token(user, azp=CLIENT_ID, aud=CLIENT_ID, nonce=nonce)
        return httpx.Response(200, json=body)


def bearer_headers(user: str = "admin") -> dict[str, str]:
    """The ``Authorization`` header of a fresh webapp token of the user (AUT-02)."""
    return {"Authorization": f"Bearer {FakeIssuer().token(user)}"}

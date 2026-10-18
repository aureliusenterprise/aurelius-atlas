"""The OIDC relying party: discovery, JWKS, token verification and the token endpoints (AUTH-03, AUTH-06, AUTH-07).

Ports what the Keycloak Spring adapter of Atlas 2.4.0 does for ``atlas.authentication.method.keycloak``:
validate tokens against the issuer's JWKS (``AtlasKeycloakAuthenticationProvider``) and run the browser
code flow (the ``KeycloakAuthenticationEntryPoint`` and processing filter of ``AtlasSecurityConfig``).
"""

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from pydantic import BaseModel, ConfigDict, HttpUrl

LOGGER = logging.getLogger(__name__)

DISCOVERY_PATH = "/.well-known/openid-configuration"
REFRESH_SKEW_SECONDS = 60
"""Refresh the session's access token at most this long before it expires (AUTH-09).

Capped to half of each token's own lifetime, so a short-lived issuer (the dev realm issues 60 s tokens)
is refreshed within its lifetime instead of on every request the moment the token is minted.
"""

KEYS_TTL_SECONDS = 3600
"""How long the issuer's JWKS is cached before it is fetched again; a rotated kid reloads it sooner."""

MALFORMED_JWT_ERROR = "malformed token"
AUDIENCE_MISMATCH_ERROR = "token audience mismatch"
NONCE_MISMATCH_ERROR = "id_token nonce mismatch"
NO_SUBJECT_ERROR = "token carries no subject"
NOT_BEARER_ERROR = "not an access token"


class OpenIdConfig(BaseModel):
    """The issuer fields the server needs from its ``.well-known/openid-configuration``."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    jwks_uri: HttpUrl
    end_session_endpoint: HttpUrl | None = None


class OidcError(Exception):
    """The issuer could not be reached or answered wrongly; a caller failure, not the client's."""


class TokenError(OidcError):
    """A token the issuer handed back cannot be verified (AUTH-07, AUTH-03)."""


@dataclass
class Tokens:
    """The tokens of an exchange or refresh."""

    access_token: str
    refresh_token: str | None
    expires_at: float
    """Monotonic time the access token expires at."""

    lifetime_seconds: float = 300.0
    """The issued access token's lifetime (``expires_in``): the guard caps its refresh window by it."""

    claims: dict[str, Any] = field(default_factory=dict)


def _bearer(token: str) -> str:
    return f"Bearer {token}"


class OidcClient:
    """Discovery, JWKS and token handling for one issuer and client (DD-037)."""

    def __init__(
        self,
        *,
        issuer: HttpUrl,
        client_id: str,
        client_secret: str,
        ca_file: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._issuer = str(issuer).rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = http_client or httpx.AsyncClient(verify=ca_file or True, timeout=10.0)
        self._config: OpenIdConfig | None = None
        self._keys: dict[str, RSAPublicKey] = {}
        self._keys_at: float = 0.0

    async def aclose(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def config(self) -> OpenIdConfig:
        """The issuer's OpenID configuration, fetched once (AUTH-06)."""
        if self._config is None:
            payload = await self._get(f"{self._issuer}{DISCOVERY_PATH}")
            self._config = OpenIdConfig.model_validate(payload)
        return self._config

    async def authorize_url(self, *, redirect_uri: str, state: str, nonce: str | None = None) -> tuple[str, str]:
        """The issuer's authorization URL for a browser login, and the PKCE verifier to pair with it.

        Returns:
            The URL to redirect the browser to and the ``code_verifier`` for the code exchange.
        """
        config = await self.config()
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if nonce is not None:
            params["nonce"] = nonce
        url = httpx.URL(str(config.authorization_endpoint), params=params)
        return str(url), verifier

    async def end_session_url(self, *, post_logout_redirect_uri: str) -> str | None:
        """The issuer's end-session URL, or None when the issuer offers none."""
        config = await self.config()
        if config.end_session_endpoint is None:
            return None
        params = {"client_id": self._client_id, "post_logout_redirect_uri": post_logout_redirect_uri}
        return str(httpx.URL(str(config.end_session_endpoint), params=params))

    async def exchange(self, *, code: str, code_verifier: str, redirect_uri: str, nonce: str) -> Tokens:
        """Exchange an authorization code for tokens and verify them (AUTH-07).

        The ``id_token`` proves the login — its ``nonce`` must belong to this flow — but the session's
        principal comes from the verified ``access_token``, as ``AtlasKeycloakAuthenticationProvider``
        reads its roles from the access token too: Keycloak keeps realm and client roles out of the
        ``id_token``. This also matches ``refresh``, whose response carries no ``id_token`` at all.

        Raises:
            TokenError: the exchange failed or a token does not verify.
        """
        config = await self.config()
        payload = await self._token_request(
            config,
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
        )
        await self._verify_jwt(payload["id_token"], nonce=nonce)  # the login belongs to this flow
        claims = await self._verify_jwt(payload["access_token"], expect_bearer=True)
        return self._tokens(payload, claims)

    async def refresh(self, refresh_token: str) -> Tokens:
        """Refresh the tokens of a session (AUTH-09).

        The response's ``access_token`` is verified like every other one and its claims returned:
        the session's identity is taken from them after a refresh, so a role change at the issuer
        reaches the session (a refresh response carries no ``id_token`` — the new access token is
        the fresh proof of the user and its roles).

        Raises:
            TokenError: the issuer refused the refresh token, or its access token does not verify.
        """
        config = await self.config()
        payload = await self._token_request(
            config,
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        claims = await self._verify_jwt(payload["access_token"], expect_bearer=True)
        return self._tokens(payload, claims)

    async def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify a bearer access token against the issuer's JWKS (AUTH-03).

        Keycloak's own ``typ`` must say ``Bearer``: an ID token proves a login, not API access, and
        is refused here even though it is signed by the same issuer for the same client.

        Raises:
            TokenError: the token does not verify.
            OidcError: the JWKS could not be fetched.
        """
        return await self._verify_jwt(token, expect_bearer=True)

    async def _verify_jwt(self, token: str, *, nonce: str | None = None, expect_bearer: bool = False) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise TokenError(MALFORMED_JWT_ERROR) from e
        key = await self._key(header.get("kid"))
        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False},
                leeway=30,
            )
        except jwt.PyJWTError as e:
            problem = f"token does not verify: {e}"
            raise TokenError(problem) from e
        if expect_bearer and str(claims.get("typ", "")).lower() != "bearer":
            # AUTH-03: Keycloak marks its access tokens with the payload claim ``typ: Bearer`` and its
            # id tokens with ``typ: ID``. An ID token is proof of a login, not an API credential, and
            # is refused here although the same issuer signs it for the same client.
            raise TokenError(NOT_BEARER_ERROR)
        if not self._audience_matches(claims):
            raise TokenError(AUDIENCE_MISMATCH_ERROR)
        if nonce is not None and claims.get("nonce") != nonce:
            raise TokenError(NONCE_MISMATCH_ERROR)
        if not claims.get("preferred_username") and not claims.get("sub"):
            raise TokenError(NO_SUBJECT_ERROR)
        return claims

    async def _key(self, kid: str | None) -> RSAPublicKey:
        if not self._keys or time.monotonic() - self._keys_at > KEYS_TTL_SECONDS:
            await self._load_keys()
        if kid is not None and (key := self._keys.get(kid)) is not None:
            return key
        await self._load_keys()  # the key may have rotated (AUTH-03)
        if kid is not None and (key := self._keys.get(kid)) is not None:
            return key
        problem = f"no key for kid {kid!r}"
        raise TokenError(problem)

    async def _load_keys(self) -> None:
        config = await self.config()
        payload = await self._get(str(config.jwks_uri))
        # JWKS entries are public keys by definition; a JWK that parses to anything else is not a key.
        self._keys = {
            k["kid"]: key
            for k in payload["keys"]
            if "kid" in k and isinstance(key := RSAAlgorithm.from_jwk(k), RSAPublicKey)
        }
        self._keys_at = time.monotonic()

    async def _token_request(self, config: OpenIdConfig, form: dict[str, str]) -> dict[str, Any]:
        payload = await self._post(str(config.token_endpoint), form)
        if "access_token" not in payload:
            problem = f"token response carries no access_token: {payload.get('error')}"
            raise TokenError(problem)
        return payload

    async def _get(self, url: str) -> dict[str, Any]:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            problem = f"cannot reach the issuer: {e}"
            raise OidcError(problem) from e
        return response.json()

    async def _post(self, url: str, form: dict[str, str]) -> dict[str, Any]:
        try:
            response = await self._client.post(url, data=form)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            problem = f"the issuer refused the request: {e.response.status_code}"
            raise TokenError(problem) from e
        except httpx.HTTPError as e:
            problem = f"cannot reach the issuer: {e}"
            raise OidcError(problem) from e
        return response.json()

    def _tokens(self, payload: dict[str, Any], claims: dict[str, Any]) -> Tokens:
        lifetime = float(payload.get("expires_in", 300))
        return Tokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=time.monotonic() + lifetime,
            lifetime_seconds=lifetime,
            claims=claims,
        )

    def _audience_matches(self, claims: dict[str, Any]) -> bool:
        """Whether the client appears in the token's ``azp`` or ``aud`` claim, as the adapter requires."""
        if claims.get("azp") == self._client_id:
            return True
        match claims.get("aud"):
            case str() as aud:
                return aud == self._client_id
            case list() as aud_list:
                return self._client_id in aud_list
            case _:
                return False


def principal_of(claims: dict[str, Any], client_id: str) -> tuple[str, list[str]]:
    """The user name and groups a token carries, as ``AtlasKeycloakAuthenticationProvider`` reads them (ADM-06).

    The groups are the token's realm roles unioned with the client roles of the relying party, deduplicated
    in first-seen order; Keycloak namespaces client roles under ``resource_access.<client-id>.roles``.
    """
    username = str(claims.get("preferred_username") or claims.get("sub") or "")
    groups: list[str] = []
    for role in claims.get("realm_access", {}).get("roles", []):
        if role not in groups:
            groups.append(str(role))
    for role in claims.get("resource_access", {}).get(client_id, {}).get("roles", []):
        if role not in groups:
            groups.append(str(role))
    return username, groups

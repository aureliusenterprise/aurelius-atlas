"""The OIDC relying party: discovery, JWKS, verification and the token endpoints (AUTH-03, AUTH-06, AUTH-07).

A `httpx.MockTransport` stands in for Keycloak: it answers the three issuer URLs the client asks for,
and the tokens it hands back are signed with a throwaway RSA key so verification runs for real.
"""

import base64
import hashlib
import json
import time
from typing import Any

import httpx
import jwt
import pytest
from aurelius_atlas_server.auth.oidc import OidcClient, OidcError, TokenError, principal_of
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from pydantic import HttpUrl

ISSUER = "https://keycloak.localhost:8443/realms/master"
ISSUER_URL = HttpUrl(ISSUER)
CLIENT_ID = "aurelius-atlas"
REDIRECT_URI = "https://localhost:8444/api/atlas/auth/callback"
KID = "test-key"
RP_CREDENTIAL = "rp-secret"
DEAD_HOST_ERROR = "dead"
ISSUER_AT = "at"
ISSUER_RT = "rt"
ISSUER_AT2 = "at-2"
ISSUER_RT2 = "rt-2"


@pytest.fixture(scope="module")
def private_key() -> rsa.RSAPrivateKey:
    """A throwaway signing key for the fake issuer."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwk(private_key: rsa.RSAPrivateKey, kid: str = KID) -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return jwk


def _token(
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
    *,
    kid: str | None = KID,
    alg: str = "RS256",
) -> str:
    header = {"alg": alg, "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid
    return jwt.encode(claims, private_key, algorithm=alg, headers=header)


def _claims(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401 - claim values are arbitrary JSON
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "azp": CLIENT_ID,
        "sub": "11111111-1111-1111-1111-111111111111",
        "preferred_username": "writer",
        "exp": now + 300,
        "iat": now,
        "realm_access": {"roles": ["ADMIN", "writer"]},
        "resource_access": {CLIENT_ID: {"roles": ["aurelius-write"]}},
    }
    claims.update(overrides)
    return claims


def _issuer(private_key: rsa.RSAPrivateKey, tokens: dict[str, Any] | None = None) -> httpx.MockTransport:
    """The transport answering discovery, JWKS and the token endpoint for one client."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
                    "token_endpoint": f"{ISSUER}/protocol/openid-connect/token",
                    "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
                    "end_session_endpoint": f"{ISSUER}/protocol/openid-connect/logout",
                },
            )
        if request.url.path.endswith("/protocol/openid-connect/certs"):
            return httpx.Response(200, json={"keys": [_jwk(private_key)]})
        if request.url.path.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json=tokens)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _client(private_key: rsa.RSAPrivateKey, tokens: dict[str, Any] | None = None) -> OidcClient:
    return OidcClient(
        issuer=ISSUER_URL,
        client_id=CLIENT_ID,
        client_secret=RP_CREDENTIAL,
        http_client=httpx.AsyncClient(transport=_issuer(private_key, tokens)),
    )


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.authorize_url", rules=["AUTH-06"])
async def test__the_authorization_url_starts_a_code_flow_with_pkce(private_key: rsa.RSAPrivateKey) -> None:
    """The login URL is the issuer's authorization endpoint with the code-flow parameters and a verifier."""
    client = _client(private_key)
    url, verifier = await client.authorize_url(redirect_uri=REDIRECT_URI, state="st8te", nonce="n0nce")

    params = httpx.URL(url).params
    assert url.startswith(f"{ISSUER}/protocol/openid-connect/auth?")
    assert params["response_type"] == "code"
    assert params["client_id"] == CLIENT_ID
    assert params["redirect_uri"] == REDIRECT_URI
    assert params["scope"] == "openid"
    assert params["state"] == "st8te"
    assert params["nonce"] == "n0nce"
    assert params["code_challenge_method"] == "S256"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert params["code_challenge"] == challenge
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.verify_access_token", rules=["AUTH-03"])
async def test__a_bearer_token_the_issuer_signs_verifies(private_key: rsa.RSAPrivateKey) -> None:
    """A token signed by the issuer with this client's audience gives its claims back."""
    client = _client(private_key)
    token = _token(private_key, _claims())

    claims = await client.verify_access_token(token)

    assert claims["preferred_username"] == "writer"
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.verify_access_token", rules=["AUTH-03"])
@pytest.mark.parametrize(
    ("claim_overrides", "problem"),
    [
        ({"iss": "https://evil.example/realms/master"}, "issuer"),
        ({"azp": "someone-else", "aud": "someone-else"}, "audience"),
        ({"exp": int(time.time()) - 3600}, "expired"),
    ],
    ids=["wrong-issuer", "wrong-audience", "expired"],
)
async def test__a_bearer_token_that_does_not_verify_is_rejected(
    private_key: rsa.RSAPrivateKey, claim_overrides: dict[str, Any], problem: str
) -> None:
    """A token from another issuer, for another client, or past its expiry is refused (AUTH-03)."""
    client = _client(private_key)
    _ = problem
    token = _token(private_key, _claims(**claim_overrides))

    with pytest.raises(TokenError):
        await client.verify_access_token(token)
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.verify_access_token", rules=["AUTH-03"])
async def test__a_rotated_key_is_found_by_reloading_the_jwks(private_key: rsa.RSAPrivateKey) -> None:
    """A token whose key is new since the JWKS was cached verifies after one reload."""
    rotated = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/a",
                    "token_endpoint": f"{ISSUER}/t",
                    "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
                },
            )
        if request.url.path.endswith("/certs"):
            calls.append(request.url.path)
            keys = [_jwk(private_key)] if len(calls) == 1 else [_jwk(private_key), _jwk(rotated, kid="rotated")]
            return httpx.Response(200, json={"keys": keys})
        return httpx.Response(404)

    client = OidcClient(
        issuer=ISSUER_URL,
        client_id=CLIENT_ID,
        client_secret=RP_CREDENTIAL,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    await client.verify_access_token(_token(private_key, _claims()))  # warms the JWKS cache

    claims = await client.verify_access_token(_token(rotated, _claims(), kid="rotated"))
    assert claims["preferred_username"] == "writer"
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.verify_access_token", rules=["AUTH-03"])
async def test__a_token_signed_by_nobody_we_trust_is_rejected(private_key: rsa.RSAPrivateKey) -> None:
    """A token signed with another key does not verify, whatever it claims."""
    stranger = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = _client(private_key)

    with pytest.raises(TokenError):
        await client.verify_access_token(_token(stranger, _claims()))
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.exchange", rules=["AUTH-07"])
async def test__the_callback_exchange_verifies_the_id_token(private_key: rsa.RSAPrivateKey) -> None:
    """The code exchange returns verified tokens; the id_token's nonce must match the login's."""
    id_token = _token(private_key, _claims(nonce="n0nce"))
    access_token = _token(private_key, _claims())
    tokens = {"access_token": access_token, "refresh_token": ISSUER_RT, "expires_in": 300, "id_token": id_token}
    client = _client(private_key, tokens)

    exchanged = await client.exchange(code="abc", code_verifier="verifier", redirect_uri=REDIRECT_URI, nonce="n0nce")

    assert exchanged.access_token == access_token
    assert exchanged.refresh_token == ISSUER_RT
    assert exchanged.claims["preferred_username"] == "writer"
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.exchange", rules=["AUTH-07"])
async def test__the_session_claims_come_from_the_access_token(private_key: rsa.RSAPrivateKey) -> None:
    """The session's principal comes from the access token, which is where Keycloak puts the roles.

    The id_token of a real Keycloak carries no realm_access; a session built from it would hold no
    groups. Atlas's provider reads the access token, so the exchange verifies it and takes its claims.
    """
    id_token = _token(private_key, _claims(nonce="n0nce", realm_access=None, resource_access=None))
    access_token = _token(private_key, _claims(aud="aurelius"))  # what a real Keycloak issues: aud=resource
    tokens = {
        "access_token": access_token,
        "refresh_token": ISSUER_RT,
        "expires_in": 300,
        "id_token": id_token,
    }
    client = _client(private_key, tokens)

    exchanged = await client.exchange(code="abc", code_verifier="verifier", redirect_uri=REDIRECT_URI, nonce="n0nce")

    assert exchanged.claims["realm_access"] == {"roles": ["ADMIN", "writer"]}
    username, groups = principal_of(exchanged.claims, CLIENT_ID)
    assert username == "writer"
    assert groups == ["ADMIN", "writer", "aurelius-write"]
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.exchange", rules=["AUTH-07"])
async def test__an_id_token_with_the_wrong_nonce_is_refused(private_key: rsa.RSAPrivateKey) -> None:
    """A replayed id_token (the nonce belongs to another login) is refused and never exchanged."""
    id_token = _token(private_key, _claims(nonce="other-nonce"))
    tokens = {"access_token": ISSUER_AT, "expires_in": 300, "id_token": id_token}
    client = _client(private_key, tokens)

    with pytest.raises(TokenError, match="nonce"):
        await client.exchange(code="abc", code_verifier="verifier", redirect_uri=REDIRECT_URI, nonce="n0nce")
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.refresh", rules=["AUTH-09"])
async def test__a_refresh_gives_new_access_without_an_id_token(private_key: rsa.RSAPrivateKey) -> None:
    """The refresh grant returns a new access token; no id_token is verified."""
    tokens = {"access_token": ISSUER_AT2, "refresh_token": ISSUER_RT2, "expires_in": 300}
    client = _client(private_key, tokens)

    refreshed = await client.refresh("rt")

    assert refreshed.access_token == ISSUER_AT2
    assert refreshed.refresh_token == ISSUER_RT2
    assert refreshed.claims == {}
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.refresh", rules=["AUTH-09"])
async def test__a_refused_token_request_is_a_token_error() -> None:
    """When the issuer refuses the grant (400 invalid_grant) the client raises TokenError, not OidcError."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(
            200,
            json={
                "issuer": ISSUER,
                "authorization_endpoint": f"{ISSUER}/a",
                "token_endpoint": f"{ISSUER}/t",
                "jwks_uri": f"{ISSUER}/certs",
            },
        )

    client = OidcClient(
        issuer=ISSUER_URL,
        client_id=CLIENT_ID,
        client_secret=RP_CREDENTIAL,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TokenError):
        await client.refresh("expired-refresh-token")
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.config", rules=["AUTH-06"])
async def test__an_unreachable_issuer_is_an_oidc_error() -> None:
    """Discovery against a dead issuer raises OidcError, which the guard answers as 500."""

    def refuse(request: httpx.Request) -> httpx.Response:
        _ = request
        raise httpx.ConnectError(DEAD_HOST_ERROR)

    client = OidcClient(
        issuer=ISSUER_URL,
        client_id=CLIENT_ID,
        client_secret=RP_CREDENTIAL,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(refuse)),
    )

    with pytest.raises(OidcError):
        await client.config()
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.principal_of", rules=["ADM-06"])
def test__the_principal_reads_the_user_and_its_realm_and_client_roles() -> None:
    """The user name is preferred_username; the groups are realm roles then client roles, deduplicated."""
    claims = {
        "preferred_username": "writer",
        "sub": "1111",
        "realm_access": {"roles": ["ADMIN", "writer"]},
        "resource_access": {CLIENT_ID: {"roles": ["aurelius-write", "ADMIN"]}},
    }

    username, groups = principal_of(claims, CLIENT_ID)

    assert username == "writer"
    assert groups == ["ADMIN", "writer", "aurelius-write"]


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.principal_of", rules=["ADM-06"])
def test__a_token_without_a_preferred_username_falls_back_to_sub() -> None:
    """A service-token with only a sub still names its principal; missing roles give no groups."""
    username, groups = principal_of({"sub": "svc-account"}, CLIENT_ID)

    assert username == "svc-account"
    assert groups == []


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.end_session_url", rules=["AUTH-10"])
async def test__the_end_session_url_returns_the_browser_to_the_origin(private_key: rsa.RSAPrivateKey) -> None:
    """Logout sends the browser to the issuer's end-session endpoint with the registered redirect."""
    client = _client(private_key)

    url = await client.end_session_url(post_logout_redirect_uri="https://localhost:8444/")

    assert url is not None
    assert url.startswith(f"{ISSUER}/protocol/openid-connect/logout?")
    assert httpx.URL(url).params["post_logout_redirect_uri"] == "https://localhost:8444/"
    assert httpx.URL(url).params["client_id"] == CLIENT_ID
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.end_session_url", rules=["AUTH-10"])
async def test__an_issuer_without_an_end_session_endpoint_offers_no_url() -> None:
    """Discovery without an end_session_endpoint gives None: logout lands on the origin instead."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/a",
                    "token_endpoint": f"{ISSUER}/t",
                    "jwks_uri": f"{ISSUER}/certs",
                },
            )
        return httpx.Response(404)

    client = OidcClient(
        issuer=ISSUER_URL,
        client_id=CLIENT_ID,
        client_secret=RP_CREDENTIAL,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await client.end_session_url(post_logout_redirect_uri="https://localhost:8444/") is None
    await client.aclose()


@pytest.mark.covers("aurelius_atlas_server.auth.oidc.OidcClient.aclose", rules=["AUTH-06"])
async def test__closing_the_client_closes_its_connections(private_key: rsa.RSAPrivateKey) -> None:
    """The client's connections close with it, which the lifespan does when the server stops."""
    transport = _issuer(private_key, None)
    http = httpx.AsyncClient(transport=transport)
    client = OidcClient(issuer=ISSUER_URL, client_id=CLIENT_ID, client_secret=RP_CREDENTIAL, http_client=http)

    await client.aclose()

    assert http.is_closed

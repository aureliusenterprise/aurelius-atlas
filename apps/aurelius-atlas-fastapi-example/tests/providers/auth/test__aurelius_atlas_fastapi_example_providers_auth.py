from unittest.mock import Mock

import httpx
import jwt
import pytest
from aurelius_atlas_fastapi_example.models import Settings
from aurelius_atlas_fastapi_example.providers import auth
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pybreaker import CircuitBreaker


def build_credentials(token: str) -> HTTPAuthorizationCredentials:
    """Create an HTTPAuthorizationCredentials object with the given bearer token."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test__auth_base_url_builds_realm_url(auth_base_url: str, auth_settings: Settings) -> None:
    """Auth base URL provider should compose the expected realm URL."""
    assert auth.auth_base_url(settings=auth_settings) == auth_base_url


def test__openid_configuration_loads_from_keycloak(
    auth_base_url: str,
    http_client: httpx.Client,
    auth_circuit_breaker: CircuitBreaker,
) -> None:
    """OpenID configuration provider should fetch well-known config from Keycloak."""
    config = auth.openid_configuration(
        auth_base_url=auth_base_url,
        http_client=http_client,
        auth_circuit_breaker=auth_circuit_breaker,
    )

    assert str(config.jwks_uri).endswith("/protocol/openid-connect/certs")


def test__jwks_loads_keys_from_keycloak(
    auth_base_url: str,
    http_client: httpx.Client,
    auth_circuit_breaker: CircuitBreaker,
) -> None:
    """JWKS provider should return at least one public key from Keycloak."""
    openid = auth.openid_configuration(
        auth_base_url=auth_base_url,
        http_client=http_client,
        auth_circuit_breaker=auth_circuit_breaker,
    )
    keys = auth.jwks(http_client=http_client, openid=openid, auth_circuit_breaker=auth_circuit_breaker)

    assert keys


def test__auth_token_extracts_bearer_token(keycloak_access_token: str) -> None:
    """Auth token provider should return the bearer token from credentials."""
    credentials = build_credentials(keycloak_access_token)

    token = auth.auth_token(credentials)

    assert token == keycloak_access_token


def test__jwk_selects_key_by_token_header(
    auth_base_url: str,
    keycloak_access_token: str,
    http_client: httpx.Client,
    auth_circuit_breaker: CircuitBreaker,
) -> None:
    """JWK provider should resolve the token's kid to a public key from the JWKS."""
    openid = auth.openid_configuration(
        auth_base_url=auth_base_url,
        http_client=http_client,
        auth_circuit_breaker=auth_circuit_breaker,
    )
    keys = auth.jwks(http_client=http_client, openid=openid, auth_circuit_breaker=auth_circuit_breaker)

    key = auth.jwk(keycloak_access_token, keys)

    assert key is not None


def test__user_info_decodes_valid_token(
    auth_base_url: str,
    keycloak_access_token: str,
    http_client: httpx.Client,
    auth_circuit_breaker: CircuitBreaker,
    auth_settings: Settings,
) -> None:
    """User info provider should decode and validate a valid Keycloak token."""
    openid = auth.openid_configuration(
        auth_base_url=auth_base_url,
        http_client=http_client,
        auth_circuit_breaker=auth_circuit_breaker,
    )
    keys = auth.jwks(http_client=http_client, openid=openid, auth_circuit_breaker=auth_circuit_breaker)

    key = auth.jwk(keycloak_access_token, keys)
    claims = auth.user_info(auth_base_url, keycloak_access_token, key, auth_settings)

    assert claims["iss"] == auth_base_url
    assert claims["azp"] == "admin-cli"


def test__user_info_rejects_wrong_audience(
    auth_base_url: str,
    keycloak_access_token: str,
    http_client: httpx.Client,
    auth_circuit_breaker: CircuitBreaker,
) -> None:
    """User info provider should reject tokens whose azp/aud do not contain the expected audience."""
    openid = auth.openid_configuration(
        auth_base_url=auth_base_url,
        http_client=http_client,
        auth_circuit_breaker=auth_circuit_breaker,
    )
    keys = auth.jwks(http_client=http_client, openid=openid, auth_circuit_breaker=auth_circuit_breaker)

    key = auth.jwk(keycloak_access_token, keys)

    wrong_audience_settings = Mock(auth_audience="some-other-client", spec=Settings)

    with pytest.raises(HTTPException, match="Invalid token audience"):
        auth.user_info(auth_base_url, keycloak_access_token, key, wrong_audience_settings)


@pytest.mark.parametrize(
    ("claims", "expected_audience", "expected"),
    [
        ({"azp": "aurelius"}, "aurelius", True),
        ({"aud": "aurelius"}, "aurelius", True),
        ({"aud": ["account", "aurelius"]}, "aurelius", True),
        ({"azp": "admin-cli", "aud": ["account"]}, "aurelius", False),
        ({}, "aurelius", False),
        ({"aud": ["account", "master-realm"]}, "aurelius", False),
    ],
)
def test__audience_matches(claims: dict, expected_audience: str, expected: bool) -> None:  # noqa: FBT001
    """Audience check should accept the expected value in azp or aud and reject otherwise."""
    assert auth._audience_matches(claims, expected_audience) is expected  # noqa: SLF001


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"realm_access": {"roles": ["aurelius-write", "offline_access"]}}, {"aurelius-write", "offline_access"}),
        ({"resource_access": {"aurelius": {"roles": ["aurelius-write"]}}}, {"aurelius-write"}),
        (
            {
                "realm_access": {"roles": ["r1"]},
                "resource_access": {"aurelius": {"roles": ["c1"]}, "account": {"roles": ["c2"]}},
            },
            {"r1", "c1", "c2"},
        ),
        ({}, set()),
        ({"realm_access": {"roles": "not-a-list"}}, set()),
        ({"resource_access": {"aurelius": {"no-roles": True}}}, set()),
        ({"resource_access": "malformed"}, set()),
    ],
)
def test__token_roles_collects_realm_and_client_roles(claims: dict, expected: set[str]) -> None:
    """Role collection should union realm and per-client roles and ignore malformed claims."""
    assert auth._token_roles(claims) == expected  # noqa: SLF001


def test__require_write_access_allows_role_holder() -> None:
    """A token carrying the configured write role passes the authorization gate."""
    settings = Mock(auth_write_role="aurelius-write", spec=Settings)
    claims = {"sub": "u", "realm_access": {"roles": ["aurelius-write"]}}

    assert auth.require_write_access(claims, settings) is claims


def test__require_write_access_rejects_missing_role() -> None:
    """A valid token without the write role must not mutate entities."""
    settings = Mock(auth_write_role="aurelius-write", spec=Settings)

    with pytest.raises(HTTPException, check=lambda e: e.status_code == 403, match="Insufficient permissions"):
        auth.require_write_access({"sub": "u", "realm_access": {"roles": ["viewer"]}}, settings)


def test__require_write_access_disabled_when_role_empty() -> None:
    """An empty configured role disables the check (development only — validator enforces it)."""
    settings = Mock(auth_write_role="", spec=Settings)
    claims = {"sub": "u"}

    assert auth.require_write_access(claims, settings) is claims


def test__user_info_rejects_wrong_issuer(
    auth_base_url: str,
    keycloak_access_token: str,
    http_client: httpx.Client,
    auth_circuit_breaker: CircuitBreaker,
    auth_settings: Settings,
) -> None:
    """User info provider should reject tokens when issuer does not match configured realm."""
    openid = auth.openid_configuration(
        auth_base_url=auth_base_url,
        http_client=http_client,
        auth_circuit_breaker=auth_circuit_breaker,
    )
    keys = auth.jwks(http_client=http_client, openid=openid, auth_circuit_breaker=auth_circuit_breaker)

    key = auth.jwk(keycloak_access_token, keys)

    with pytest.raises(HTTPException, match="Invalid token issuer"):
        auth.user_info(f"{auth_base_url}/wrong", keycloak_access_token, key, auth_settings)


def test__jwk_rejects_unknown_key_id() -> None:
    """JWK provider should raise 401 when token kid is missing from provided JWKS map."""
    token = jwt.encode(
        {"sub": "test-sub"},
        key="test-secret",
        algorithm="HS256",
        headers={"kid": "missing-key"},
    )

    with pytest.raises(HTTPException, match="Authentication key not available"):
        auth.jwk(token, {})


def test__auth_circuit_breaker_configuration(auth_settings: Settings) -> None:
    """Circuit breaker should be configured with settings values."""
    cb = auth.auth_circuit_breaker(settings=auth_settings)

    assert cb.name == "auth_circuit_breaker"
    assert cb.fail_max == 5
    assert cb.reset_timeout == 60.0


def test__openid_configuration_returns_503_when_circuit_open(
    auth_base_url: str,
    http_client: httpx.Client,
) -> None:
    """OpenID configuration should return 503 when circuit breaker is open."""
    cb = CircuitBreaker(fail_max=1, reset_timeout=60.0)
    cb.open()

    with pytest.raises(
        HTTPException,
        check=lambda e: e.status_code == 503,
        match="temporarily unavailable",
    ):
        auth.openid_configuration(
            auth_base_url=auth_base_url,
            http_client=http_client,
            auth_circuit_breaker=cb,
        )


def test__jwks_returns_503_when_circuit_open(
    http_client: httpx.Client,
) -> None:
    """JWKS should return 503 when circuit breaker is open."""
    cb = CircuitBreaker(fail_max=1, reset_timeout=60.0)
    cb.open()

    with pytest.raises(
        HTTPException,
        check=lambda e: e.status_code == 503,
        match="temporarily unavailable",
    ):
        auth.jwks(
            http_client=http_client,
            openid=None,  # type: ignore[arg-type]
            auth_circuit_breaker=cb,
        )

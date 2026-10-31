"""Unit tests for the shared Keycloak verifier (8.0, AUX-01..AUX-05)."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_auth.auth import AuthConfig, KeycloakAuth
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient


def _app(auth: KeycloakAuth) -> FastAPI:
    """A tiny application guarding three routes with the three dependencies."""
    app = FastAPI()

    @app.get("/whoami", dependencies=[auth.require_auth])
    def whoami() -> dict:
        return {"ok": True}

    @app.post("/write", dependencies=[auth.require_write])
    def write() -> dict:
        return {"ok": True}

    # The Depends default (not Annotated) is deliberate: with PEP 563 string
    # annotations, FastAPI resolves markers against module globals, and `auth`
    # only exists in this closure's scope.
    @app.get("/raw")
    def raw(raw_token: str = Depends(auth.bearer)) -> dict:  # noqa: FAST002
        return {"token": raw_token}

    return app


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(auth: KeycloakAuth) -> TestClient:
    """A test client for an app guarded by the fake-issuer verifier."""
    return TestClient(_app(auth))


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.__init__",
    "aurelius_atlas_auth.auth.KeycloakAuth.close",
    rules=["AUX-01"],
)
def test__init__normalises_the_issuer_and_close_is_safe() -> None:
    """The issuer root keeps one slash before /realms/, and closing twice is fine."""
    instance = KeycloakAuth(AuthConfig(server_url="https://issuer:8443/", realm="master", audience="aux-test"))
    assert instance.base_url == "https://issuer:8443/realms/master"
    instance.close()
    instance.close()


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    "aurelius_atlas_auth.auth.KeycloakAuth.require_auth",
    rules=["AUX-02"],
)
def test__a_valid_token_reveals_its_claims(client: TestClient, token: Callable[..., str]) -> None:
    """A token signed by the issuer's key with this audience verifies (AUX-02)."""
    assert client.get("/whoami", headers=_bearer(token())).status_code == 200


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__an_expired_token_is_401(client: TestClient, token: Callable[..., str]) -> None:
    """Expiry is verified (AUX-02)."""
    assert client.get("/whoami", headers=_bearer(token(expires_in=-30))).status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__a_foreign_issuer_is_401(client: TestClient, token: Callable[..., str]) -> None:
    """The issuer claim must be this realm (AUX-02)."""
    forged = token(issuer="https://evil.example/realms/master")
    assert client.get("/whoami", headers=_bearer(forged)).status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__a_token_signed_by_an_unknown_key_is_401(
    client: TestClient,
    token: Callable[..., str],
    foreign_key: rsa.RSAPrivateKey,
) -> None:
    """A token with the known kid but a foreign signature fails (AUX-02)."""
    assert client.get("/whoami", headers=_bearer(token(key=foreign_key))).status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__an_unknown_kid_is_401(client: TestClient, token: Callable[..., str]) -> None:
    """The JWKS has no key for the token's kid (AUX-02)."""
    assert client.get("/whoami", headers=_bearer(token(kid="rotated-key"))).status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__a_non_rs256_algorithm_is_401(client: TestClient, token: Callable[..., str]) -> None:
    """Only RS256 is accepted (AUX-02): a header forged to HS256 is refused."""
    _, payload, signature = token().split(".")
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "kid": "test-key", "typ": "JWT"}).encode()).rstrip(
        b"="
    )
    forged = f"{header.decode()}.{payload}.{signature}"
    assert client.get("/whoami", headers=_bearer(forged)).status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-03"],
)
def test__audience_accepted_from_azp_or_the_aud_list(client: TestClient, token: Callable[..., str]) -> None:
    """The union of azp and aud is the audience set (AUX-03)."""
    assert client.get("/whoami", headers=_bearer(token(azp="aux-test", audience=None))).status_code == 200
    assert client.get("/whoami", headers=_bearer(token(azp=None, audience=["aux-test", "other"]))).status_code == 200


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-03"],
)
def test__a_foreign_audience_is_401(client: TestClient, token: Callable[..., str]) -> None:
    """A token for another client is rejected, even from this issuer (AUX-03)."""
    forged = token(azp="other-client", audience="other-client")
    assert client.get("/whoami", headers=_bearer(forged)).status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.require_write_access",
    "aurelius_atlas_auth.auth.KeycloakAuth.require_write",
    rules=["AUX-04"],
)
def test__the_write_role_from_the_realm_grants_write(client: TestClient, token: Callable[..., str]) -> None:
    """realm_access roles count (AUX-04)."""
    assert client.post("/write", headers=_bearer(token(realm_roles=["aux-write"]))).status_code == 200


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.require_write_access",
    rules=["AUX-04"],
)
def test__the_write_role_from_this_client_grants_write(client: TestClient, token: Callable[..., str]) -> None:
    """resource_access under the audited client counts (AUX-04)."""
    assert client.post("/write", headers=_bearer(token(client_roles={"aux-test": ["aux-write"]}))).status_code == 200


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.require_write_access",
    rules=["AUX-04"],
)
def test__a_role_under_another_client_is_403(client: TestClient, token: Callable[..., str]) -> None:
    """Client roles are namespaced: a same-named role of another client is not ours (AUX-04)."""
    assert client.post("/write", headers=_bearer(token(client_roles={"other": ["aux-write"]}))).status_code == 403


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.require_write_access",
    rules=["AUX-04"],
)
def test__no_write_role_at_all_is_403(client: TestClient, token: Callable[..., str]) -> None:
    """A valid user token without the role is denied (AUX-04)."""
    assert client.post("/write", headers=_bearer(token())).status_code == 403


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.require_write_access",
    rules=["AUX-04"],
)
def test__an_empty_write_role_disables_the_gate(
    auth_config: AuthConfig,
    token: Callable[..., str],
    issuer_client_factory: Callable[..., httpx.Client],
) -> None:
    """write_role='' is the development posture: any valid token writes."""
    auth = KeycloakAuth(
        AuthConfig(
            server_url=auth_config.server_url,
            realm=auth_config.realm,
            audience=auth_config.audience,
            write_role="",
        ),
        http=issuer_client_factory(),
    )
    assert TestClient(_app(auth)).post("/write", headers=_bearer(token())).status_code == 200


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.bearer",
    "aurelius_atlas_auth.auth.KeycloakAuth.require_bearer",
    rules=["AUX-05"],
)
def test__require_bearer_yields_the_raw_token_for_forwarding(client: TestClient, token: Callable[..., str]) -> None:
    """The scheme's credential passes through verbatim, unverified (AUX-05)."""
    minted = token()
    response = client.get("/raw", headers=_bearer(minted))
    assert response.status_code == 200
    assert response.json()["token"] == minted


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.require_bearer",
    rules=["AUX-05"],
)
def test__a_missing_credential_is_rejected(client: TestClient) -> None:
    """Without the header, the scheme rejects before the route runs (AUX-05)."""
    assert client.get("/raw").status_code == 401  # FastAPI's HTTPBearer: absent credential is 401
    assert client.get("/whoami").status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__a_down_issuer_is_503_not_a_hang(
    auth_config: AuthConfig,
    token: Callable[..., str],
    issuer_client_factory: Callable[..., httpx.Client],
) -> None:
    """An unreachable issuer is an availability failure (AUX-02)."""
    auth = KeycloakAuth(auth_config, http=issuer_client_factory(fail=True))
    assert TestClient(_app(auth)).get("/whoami", headers=_bearer(token())).status_code == 503


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__the_jwks_is_fetched_once_and_cached(
    audience: str,
    token: Callable[..., str],
    issuer_handler_factory: Callable[..., Any],
) -> None:
    """The signing keys are cached: a second token causes no new issuer call (AUX-02)."""
    calls: list[str] = []
    base = issuer_handler_factory()

    def counting(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return base(request)

    auth = KeycloakAuth(
        AuthConfig(server_url="https://keycloak.localhost:8443", realm="master", audience=audience),
        http=httpx.Client(transport=httpx.MockTransport(counting)),
    )
    credentials = _credentials(token())
    auth.user_info(credentials)
    auth.user_info(credentials)
    assert len(calls) == 2  # discovery + JWKS, once; the second user_info hits the cache
    auth.close()


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.user_info",
    rules=["AUX-02"],
)
def test__the_circuit_opens_on_repeated_issuer_failure(
    auth_config: AuthConfig,
    token: Callable[..., str],
    issuer_client_factory: Callable[..., httpx.Client],
) -> None:
    """Repeated issuer failures open the circuit: the 503 arrives without a call (AUX-02)."""
    auth = KeycloakAuth(
        AuthConfig(
            server_url=auth_config.server_url,
            realm=auth_config.realm,
            audience=auth_config.audience,
            fail_max=1,
            reset_timeout=600,
        ),
        http=issuer_client_factory(fail=True),
    )
    credentials = _credentials(token())
    with pytest.raises(HTTPException) as first:
        auth.user_info(credentials)
    assert first.value.status_code == 503
    with pytest.raises(HTTPException) as second:
        auth.user_info(credentials)
    assert second.value.status_code == 503  # breaker open, no call made
    auth.close()


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.__init__",
    rules=["AUX-01"],
)
def test__the_issuer_url_is_the_realm_path_of_the_server(base_url: str) -> None:
    """Discovery hangs off <server_url>/realms/<realm> (AUX-01)."""
    instance = KeycloakAuth(AuthConfig(server_url="https://kc:8443", realm="master", audience="aux-test"))
    assert instance.base_url == "https://kc:8443/realms/master"
    assert base_url.endswith("/realms/master")
    instance.close()


@pytest.mark.covers(
    "aurelius_atlas_auth.auth.KeycloakAuth.verify",
    "aurelius_atlas_auth.auth.AuthConfig.audiences",
    rules=["AUT-10"],
)
def test__verify_takes_a_token_of_any_accepted_audience(
    auth_config: AuthConfig, issuer_client_factory: Callable[..., httpx.Client], token: Callable[..., str]
) -> None:
    """A further audience is accepted besides the service's own; any other is refused (AUT-10)."""
    config = AuthConfig(
        server_url=auth_config.server_url,
        realm=auth_config.realm,
        audience=auth_config.audience,
        extra_audiences=("webapp",),
    )
    auth = KeycloakAuth(config, http=issuer_client_factory())
    assert config.audiences == frozenset({auth_config.audience, "webapp"})
    assert auth.verify(token(audience=None, azp="webapp"))["azp"] == "webapp"
    assert auth.verify(token())["sub"] == "user-1"
    with pytest.raises(HTTPException) as refused:
        auth.verify(token(audience=None, azp="other"))
    assert refused.value.status_code == 401
    auth.close()


@pytest.mark.covers("aurelius_atlas_auth.auth.KeycloakAuth.discovery", rules=["AUT-10"])
def test__discovery_is_fetched_once(
    auth_config: AuthConfig, issuer_handler_factory: Callable[..., Any], token: Callable[..., str]
) -> None:
    """The issuer's OpenID configuration is read once and shared with the key lookup (AUT-10)."""
    calls: list[str] = []
    handler = issuer_handler_factory()

    def counting(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return handler(request)

    auth = KeycloakAuth(auth_config, http=httpx.Client(transport=httpx.MockTransport(counting)))
    assert auth.discovery()["jwks_uri"].endswith("/certs")
    auth.verify(token())
    auth.discovery()
    assert [path.rsplit("/", 1)[-1] for path in calls] == ["openid-configuration", "certs"]
    auth.close()

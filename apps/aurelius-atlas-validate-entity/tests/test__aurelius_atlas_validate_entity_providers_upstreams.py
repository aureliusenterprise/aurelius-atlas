"""The upstream factories: the minted identity, the unconfigured leg, the breaker (VEV-04/06; DD-499, DD-500).

The mint is patched at the OTel library's ``urlopen`` — the issuer itself is
tested at home, in ``aurelius-atlas-otel``; what is tested here is the policy the
app builds on it: the bearer its client carries (VEV-04, the scanner's
``_tokens`` seam read from a service's side, DD-458's sibling), the refusal of a
refused or unconfigured mint (VEV-06), and the breaker's bounds and excludes
(DD-500).
"""

import io
import json
from typing import Any, Self
from urllib.error import URLError
from urllib.request import Request

import httpx2 as httpx
import pytest
from aurelius_atlas_otel import ClientCredentialsTokenSource, ingest
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_validate_entity.errors import UpstreamError
from aurelius_atlas_validate_entity.providers import build_upstreams, is_upstream_fact, server_breaker
from aurelius_atlas_validate_entity.providers.upstreams import (
    MINT_REFUSAL,
    MINT_UNCONFIGURED,
    _refused,
    _tokens,
)
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings
from pybreaker import CircuitBreakerError
from pydantic import HttpUrl


class FakeResponse(io.BytesIO):
    """A urlopen response: the JSON body, as a readable context manager."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


def _mint_ok() -> FakeResponse:
    """The issuer answering the client-credentials grant with a token."""
    return FakeResponse(json.dumps({"access_token": "minted-token", "expires_in": 300}).encode())


def _settings(**overrides: Any) -> ValidateEntitySettings:  # noqa: ANN401 - the settings fields under test
    """Settings for the leg: fake issuer and catalogue, secret configured unless overridden."""
    base: dict[str, Any] = {
        "auth_server_url": HttpUrl("http://issuer.test"),
        "server_base_url": HttpUrl("http://catalogue.test"),
        "server_client_secret": "leg-secret",
    }
    return ValidateEntitySettings(**{**base, **overrides})


def _leg_bearer(atlas: AtlasClient) -> str:
    """The bearer the leg's client carries: the token source it was built with (the seam under test)."""
    token = atlas._token  # noqa: SLF001 - the bearer source is the seam, as the scanner's tests read it
    return token() if callable(token) else token


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.build_upstreams", rules=["VEV-04"])
def test__the_client_carries_the_apps_own_minted_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """The built client mints by client-credentials at the settings' issuer, as its own client (VEV-04, DD-499)."""
    calls: list[str] = []
    auth_headers: list[str] = []

    def fake_urlopen(request: Request, *_args: object, **_kwargs: object) -> FakeResponse:
        calls.append(str(request.full_url))
        auth_headers.append(request.get_header("Authorization") or "")
        return _mint_ok()

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    atlas, pools = build_upstreams(_settings())

    assert _leg_bearer(atlas) == "minted-token"
    assert calls == [str(_settings().token_url)]
    assert auth_headers[0].startswith("Basic ")  # the client-credentials grant, authenticated as the app's client
    assert len(pools) == 1
    assert str(pools[0].base_url).rstrip("/") == "http://catalogue.test"


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.build_upstreams", rules=["VEV-04"])
def test__the_mint_is_minted_once_for_a_window_of_bearers(monkeypatch: pytest.MonkeyPatch) -> None:
    """One mint serves the window: the identity is minted, not minted per call (VEV-04)."""
    calls: list[str] = []

    def count_mints(request: Request, *_args: object, **_kwargs: object) -> FakeResponse:
        calls.append(str(request.full_url))
        return _mint_ok()

    monkeypatch.setattr(ingest, "urlopen", count_mints)
    atlas, _pools = build_upstreams(_settings())

    assert _leg_bearer(atlas) == "minted-token"
    assert _leg_bearer(atlas) == "minted-token"
    assert calls == [str(_settings().token_url)]  # minted once; the second read rides the cached token


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.build_upstreams", rules=["VEV-06"])
def test__a_leg_without_the_secret_refuses_every_read() -> None:
    """The join absent (VEV-06): the client still builds — the app stays live — and its bearer refuses."""
    atlas, pools = build_upstreams(_settings(server_client_secret=None))

    with pytest.raises(UpstreamError) as raised:
        _leg_bearer(atlas)

    assert raised.value.status_code == 502
    assert MINT_UNCONFIGURED in str(raised.value)
    assert len(pools) == 1


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.build_upstreams", rules=["VEV-04", "VEV-06"])
def test__a_refused_mint_is_a_refused_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """The issuer refusing the credentials is a 502 refusal, never an anonymous read (DD-196's posture, kept)."""
    refused = "connection refused"

    def refuse(_request: Request, *_args: object, **_kwargs: object) -> FakeResponse:
        raise URLError(refused)

    monkeypatch.setattr(ingest, "urlopen", refuse)
    atlas, _pools = build_upstreams(_settings())

    with pytest.raises(UpstreamError) as raised:
        _leg_bearer(atlas)

    assert raised.value.status_code == 502
    assert MINT_REFUSAL in str(raised.value)


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams._tokens", rules=["VEV-04"])
def test__the_wrapper_refuses_a_source_that_mints_nothing() -> None:
    """A source that answers None (mint failed, nothing cached) is refused, not sent anonymous (DD-196)."""

    class _StubSource(ClientCredentialsTokenSource):
        def __init__(self, token: str | None) -> None:
            self._token = token

        def bearer(self) -> str | None:
            return self._token

    refused = _tokens(_StubSource(None))  # the stub stands in for the source
    granted = _tokens(_StubSource("abc"))

    assert granted() == "abc"
    with pytest.raises(UpstreamError) as raised:
        refused()
    assert raised.value.status_code == 502


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams._refused", rules=["VEV-06"])
def test__the_unconfigured_bearer_names_the_missing_setting() -> None:
    """The refusal line names SERVER_CLIENT_SECRET: a cluster without the join is told what to set (VEV-06)."""
    with pytest.raises(UpstreamError, match="SERVER_CLIENT_SECRET"):
        _refused()


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.build_upstreams", rules=["VEV-04"])
def test__an_injected_client_keeps_its_own_pool() -> None:
    """The tests' seam (DD-205): an injected client appears in no close list."""
    mine = httpx.AsyncClient(base_url="http://catalogue.test")
    atlas, pools = build_upstreams(_settings(), atlas=AtlasClient(mine, "test-identity"))

    assert pools == []
    assert isinstance(atlas, AtlasClient)


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.is_upstream_fact", rules=["VEV-06"])
@pytest.mark.parametrize(("status", "is_fact"), [(400, True), (404, True), (429, True), (500, False), (503, False)])
def test__a_catalogue_4xx_is_a_fact_and_a_5xx_an_outage(
    status: int,
    is_fact: bool,  # noqa: FBT001 - the parametrized pair
) -> None:
    """The breaker's exclude predicate: 4xx facts reset, 5xx outages count (VEV-06, LM-13's sibling)."""
    error = type("Err", (RuntimeError,), {"status_code": status})()

    assert is_upstream_fact(error) is is_fact


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.is_upstream_fact", rules=["VEV-06"])
def test__a_transport_failure_is_an_outage() -> None:
    """A request error carries no status: an outage, counting toward the open circuit (VEV-06)."""
    error = httpx.ConnectError("refused")

    assert is_upstream_fact(error) is False


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.server_breaker", rules=["VEV-06"])
def test__the_breaker_carries_the_settings_bounds() -> None:
    """The settings' pair bounds the circuit (VEV-05 grown): the name, fail max and reset timeout."""
    breaker = server_breaker(_settings(breaker_fail_max=3, breaker_reset_timeout=12))

    assert breaker.name == "validate_entity_server"
    assert breaker.fail_max == 3
    assert breaker.reset_timeout == 12


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.server_breaker", rules=["VEV-06"])
def test__the_mint_refusal_is_an_excluded_fact() -> None:
    """An UpstreamError (the mint refusal) is excluded: it answers its own cause, never counts to an open circuit."""
    breaker = server_breaker(_settings(breaker_fail_max=1))

    for _ in range(3):  # excluded: the circuit never opens on the app's own refusal
        with pytest.raises(UpstreamError), breaker.calling():
            raise UpstreamError(502, MINT_REFUSAL)


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.upstreams.server_breaker", rules=["VEV-06"])
def test__outages_open_the_breaker_which_then_fast_fails() -> None:
    """Pybreaker's contract: fail_max counted outages open the circuit; the open circuit refuses the call."""
    breaker = server_breaker(_settings(breaker_fail_max=2))
    outage_one = "outage one"
    outage_two = "outage two"

    with pytest.raises(RuntimeError), breaker.calling():  # the first outage counts, the circuit closed
        raise RuntimeError(outage_one)
    with pytest.raises(CircuitBreakerError), breaker.calling():  # the second crosses fail_max: opened
        raise RuntimeError(outage_two)
    with pytest.raises(CircuitBreakerError), breaker.calling():
        pass  # still open: the body never runs

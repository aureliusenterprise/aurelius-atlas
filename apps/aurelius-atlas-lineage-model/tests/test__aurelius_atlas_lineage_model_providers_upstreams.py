"""Unit tests for the upstream factories: pools, breakers, clients (LM-11, LM-13, LM-15, DD-116)."""

import httpx
import pytest
from aurelius_atlas_data2model_client.client import Data2ModelClient, Data2ModelClientError
from aurelius_atlas_lineage_model.providers.upstreams import (
    atlas_breaker,
    build_upstreams,
    d2m_breaker,
    is_upstream_fact,
    upstream_http,
)
from aurelius_atlas_lineage_model.settings import LineageModelSettings
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.upstreams.upstream_http", rules=["LM-10"])
async def test__the_pool_serves_the_base_url_it_is_given(settings: LineageModelSettings) -> None:
    """The pool speaks to one upstream, with the call bound of DD-111 (the standalone container's pool)."""
    pool = upstream_http(settings, settings.atlas_base_url)
    try:
        assert str(pool.base_url) == "http://atlas.test/"
        assert pool.timeout.read == 10.0
    finally:
        await pool.aclose()


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.providers.upstreams.atlas_breaker",
    "aurelius_atlas_lineage_model.providers.upstreams.d2m_breaker",
    rules=["LM-11", "LM-15"],
)
def test__the_breakers_are_per_upstream_and_take_the_settings(settings: LineageModelSettings) -> None:
    """One breaker per integration point (LM-11), tuned by the settings (LM-15)."""
    atlas = atlas_breaker(settings)
    d2m = d2m_breaker(settings)

    assert atlas is not d2m
    assert atlas.name == "lineage_model_atlas"
    assert d2m.name == "lineage_model_data2model"
    assert atlas.fail_max == settings.breaker_fail_max == 5
    assert atlas.reset_timeout == settings.breaker_reset_timeout == 60.0
    assert atlas.current_state == "closed"


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.upstreams.is_upstream_fact", rules=["LM-13"])
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (AtlasClientError(404, None), "fact"),  # LM-05's 404: a fact about the guid
        (AtlasClientError(400, None), "fact"),  # LM-07's 400: a fact about the request
        (AtlasClientError(503, None), "outage"),  # a 5xx is an outage
        (Data2ModelClientError(400, None, None), "fact"),  # the extract's 4xx travels the same rule
        (Data2ModelClientError(502, None, None), "outage"),
        (httpx.ConnectError("down"), "outage"),  # a transport failure carries no status (CL-05)
    ],
)
def test__an_upstream_4xx_is_a_fact_everything_else_is_not(error: BaseException, expected: str) -> None:
    """pybreaker's exclude predicate: 4xx counts are facts, 5xx and transport are outages (LM-13, AUX-02)."""  # noqa: D403 - the library's name is lowercase
    assert ("fact" if is_upstream_fact(error) else "outage") == expected


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.upstreams.build_upstreams", rules=["LM-11"])
def test__the_injected_clients_bring_their_own_pools(settings: LineageModelSettings) -> None:
    """An injected pair travels through untouched, and the app owns no pool of them (DD-116)."""
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    atlas = AtlasClient(httpx.AsyncClient(base_url="http://atlas.test", transport=transport), "")
    d2m = Data2ModelClient(httpx.AsyncClient(base_url="http://data2model.test", transport=transport), "")

    built_atlas, built_d2m, pools = build_upstreams(settings, atlas, d2m)

    assert built_atlas is atlas
    assert built_d2m is d2m
    assert pools == []  # injected clients bring their own pools — the app closes none


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.upstreams.build_upstreams", rules=["LM-10"])
def test__the_upstreams_built_from_settings_own_their_pools(
    settings: LineageModelSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no injected clients the factory builds both pools, and reports them for the lifespan (DD-116)."""
    built: list[httpx.AsyncClient] = []
    real = httpx.AsyncClient

    def fake_http(_settings: LineageModelSettings, base_url: object) -> httpx.AsyncClient:
        pool = real(base_url=str(base_url), transport=httpx.MockTransport(lambda _r: httpx.Response(500)))
        built.append(pool)
        return pool

    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.upstreams.upstream_http", fake_http)

    atlas, d2m, pools = build_upstreams(settings)

    assert isinstance(atlas, AtlasClient)
    assert isinstance(d2m, Data2ModelClient)
    assert pools == built
    assert len(pools) == 2

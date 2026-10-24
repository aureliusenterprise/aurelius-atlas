"""App-wiring tests: the endpoint contract, the auth gate, liveness (LM-01, LM-08, LM-09).

The upstream circuit breakers (LM-11..LM-14, 8.5) ride on the same fake upstream:
every transport here is a mock, so the breakers' wall-clock reset is driven by
pybreaker's own management API (``half_open()``), not by sleeping.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx2 as httpx
import pytest
from aurelius_atlas_data2model_client.client import Data2ModelClient
from aurelius_atlas_lineage_model.app import create_app
from aurelius_atlas_lineage_model.globals import FAST_FAIL_ATLAS, FAST_FAIL_D2M, UPSTREAM_TIMEOUT_SECONDS
from aurelius_atlas_server_client.client import AtlasClient
from fake_upstream import FakeUpstream
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

# The graph's entity guids: the fixed UUIDs the fixtures of 8.2 use (DV-27).
E_IN = UUID("00000000-0000-4000-8000-000000000001")
P_LOAD = UUID("00000000-0000-4000-8000-000000000002")
E_OUT = UUID("00000000-0000-4000-8000-000000000003")

# The lineage body: a dataset feeding a process feeding a dataset (LM-02 fixture).
LINEAGE: dict[str, Any] = {
    "guidEntityMap": {
        str(E_IN): {"guid": str(E_IN), "typeName": "kafka_topic", "displayText": "Ingest Topic"},
        str(P_LOAD): {"guid": str(P_LOAD), "typeName": "m4i_generic_process", "displayText": "Load Job"},
        str(E_OUT): {"guid": str(E_OUT), "typeName": "hive_table", "displayText": "Sales Table"},
    },
    "relations": [
        {"fromEntityId": str(E_IN), "relationshipId": "rel-1", "toEntityId": str(P_LOAD)},
        {"fromEntityId": str(P_LOAD), "relationshipId": "rel-2", "toEntityId": str(E_OUT)},
    ],
}

# The data2model answer: the browser's document, returned verbatim (LM-01).
EXTRACTED: dict[str, Any] = {
    "model": '{"ar3_model": {"@identifier": "x"}}',
    "metadata": [{"id": str(E_IN), "data": {}}],
}


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


def _happy_upstream(upstream: FakeUpstream) -> None:
    """Set the handler: the fetch answers the lineage, the extract answers the model body."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/v2/lineage/{E_IN}":
            return upstream.json(200, LINEAGE)
        return upstream.json(200, EXTRACTED)

    upstream.handler = handler


def _breaker_app(settings: Any, auth: Any, upstream: FakeUpstream, **overrides: Any) -> FastAPI:  # noqa: ANN401  # the fixtures' settings and verifier
    """An app with breaker settings overridden — the trip tests need a small fail_max (LM-15).

    The clients ride on the recording transport, as the conftest's app fixture
    wires them (DD-111's seam); only the breaker settings differ.
    """
    transport = upstream.transport()
    return create_app(
        settings.model_copy(update=overrides),
        auth=auth,
        atlas=AtlasClient(httpx.AsyncClient(base_url="http://atlas.test", transport=transport), "test-token"),
        d2m=Data2ModelClient(httpx.AsyncClient(base_url="http://data2model.test", transport=transport), "test-token"),
    )


async def _ask(app: FastAPI, token_value: str, times: int) -> list[httpx.Response]:
    """Ask the lineage route ``times`` times, answering every response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://lineage-model") as http:
        return [await http.get("/", params={"guid": str(E_IN)}, headers=_bearer(token_value)) for _ in range(times)]


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model.routes.build_router",
    rules=["LM-01"],
)
async def test__the_extract_body_is_returned_verbatim(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """200 application/json with the data2model body, byte for byte (the screen's document)."""
    _happy_upstream(upstream)

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == EXTRACTED
    assert response.json()["model"] == EXTRACTED["model"]  # the model stays a JSON string


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-08"])
async def test__a_missing_token_is_rejected(client: httpx.AsyncClient, upstream: FakeUpstream) -> None:
    """No bearer credential is a 401; no upstream call is made (AUX-05)."""
    _happy_upstream(upstream)

    response = await client.get("/", params={"guid": str(E_IN)})

    assert response.status_code == 401
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-08"])
async def test__a_token_minted_for_another_audience_is_rejected(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A token for a client outside the audience union is a 401 (AUX-04); the legacy accepted any."""
    _happy_upstream(upstream)

    forged = token(azp="some-other-client", audience="some-other-client")
    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(forged))

    assert response.status_code == 401
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-09"])
async def test__liveness_needs_no_token(client: httpx.AsyncClient) -> None:
    """The container healthcheck answers 204, anonymous."""
    response = await client.get("/liveness")

    assert response.status_code == 204


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model.providers.auth.build_auth",
    "aurelius_atlas_lineage_model.providers.telemetry.configure_telemetry",
    rules=["LM-10"],
)
def test__the_app_is_built_from_the_settings(settings: Any) -> None:  # noqa: ANN401  # the fixture's settings object
    """The factory wires settings, auth and the upstream clients onto the app state."""
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    app = create_app(
        settings,
        atlas=AtlasClient(httpx.AsyncClient(base_url="http://atlas.test", transport=transport), "test-token"),
        d2m=Data2ModelClient(httpx.AsyncClient(base_url="http://data2model.test", transport=transport), "test-token"),
    )

    assert app.state.settings is settings
    assert app.title == "aurelius-atlas-lineage-model"
    assert app.docs_url is None  # an auxiliary API publishes no docs surface


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-01", "CL-50"])
async def test__the_app_closes_the_pools_it_built(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lifespan closes the pools the app built — nobody else's (DD-116).

    The app's pool factory is pinned to the fake transport, and the fixture's
    settings carry the upstreams as pydantic ``HttpUrl``s — their ``str()`` ends
    in a trailing slash, and the recorded paths prove the client appends its
    routes to that URL as given (CL-01).
    """
    _happy_upstream(upstream)
    built: list[httpx.AsyncClient] = []
    real_client = httpx.AsyncClient

    def fake_http(_settings: Any, base_url: Any) -> httpx.AsyncClient:  # noqa: ANN401  # the settings' HttpUrl
        pool = real_client(base_url=str(base_url), transport=upstream.transport())
        built.append(pool)
        return pool

    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.upstreams.upstream_http", fake_http)
    app = create_app(settings, auth=auth)

    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://lineage-model") as http,
        app.router.lifespan_context(app),  # start and stop: the pools open and close
    ):
        response = await http.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))
        assert response.status_code == 200

    assert [request.url.path for request in upstream.requests] == [f"/v2/lineage/{E_IN}", "/extract"]
    assert len(built) == 2
    assert all(pool.is_closed for pool in built)  # the app built them, the app closed them


def _statuses(upstream: FakeUpstream, atlas: list[int]) -> None:
    """Answer the lineage feed from ``atlas`` in order, the extract happily (the trip tests)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/v2/lineage/{E_IN}":
            return httpx.Response(atlas.pop(0))
        return upstream.json(200, EXTRACTED)

    upstream.handler = handler


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-11", "LM-15"])
def test__the_app_carries_one_breaker_per_upstream(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
) -> None:
    """Each upstream has its own circuit on the app state, closed at start-up (LM-11)."""
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    app = create_app(
        settings,
        auth=auth,
        atlas=AtlasClient(httpx.AsyncClient(base_url="http://atlas.test", transport=transport), "test-token"),
        d2m=Data2ModelClient(httpx.AsyncClient(base_url="http://data2model.test", transport=transport), "test-token"),
    )

    assert app.state.atlas_breaker is not app.state.d2m_breaker  # counted separately (LM-11)
    assert app.state.atlas_breaker.current_state == "closed"
    assert app.state.d2m_breaker.current_state == "closed"
    # The breaker settings reach the breakers (LM-15): the settings' defaults are the auth shape.
    assert app.state.atlas_breaker.fail_max == settings.breaker_fail_max == 5
    assert app.state.atlas_breaker.reset_timeout == settings.breaker_reset_timeout == 60.0


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-11", "LM-13"])
async def test__the_upstream_outages_open_the_circuit(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """Two outages (fail_max=2) open the Atlas circuit; each answered 502 as LM-07 (LM-11, LM-13)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=2)
    upstream.handler = lambda _request: httpx.Response(503)

    answers = await _ask(app, token(), 2)

    assert [answer.status_code for answer in answers] == [502, 502]
    assert app.state.atlas_breaker.current_state == "open"
    assert app.state.d2m_breaker.current_state == "closed"  # the extract never ran (LM-11)


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-12"])
async def test__an_open_circuit_answers_without_calling_the_upstream(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The open circuit's 502 names the fast-fail and reaches no upstream at all (LM-12)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=1)
    upstream.handler = lambda _request: httpx.Response(503)
    await _ask(app, token(), 1)  # the trip

    upstream.requests.clear()
    answers = await _ask(app, token(), 3)

    assert [answer.status_code for answer in answers] == [502, 502, 502]
    assert answers[0].json()["errorCode"] == "ATLAS-400-00-029"
    assert answers[0].json()["errorMessage"] == FAST_FAIL_ATLAS
    assert upstream.requests == []  # the point of the fast-fail: no connect, no timeout


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-11", "LM-12"])
async def test__a_dead_atlas_circuit_leaves_the_extract_circuit_closed(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The breakers are per upstream: the open Atlas circuit never touches the data2model one (LM-11)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=1)
    upstream.handler = lambda _request: httpx.Response(503)
    await _ask(app, token(), 1)
    app.state.atlas_breaker.open()

    answers = await _ask(app, token(), 2)

    assert [answer.status_code for answer in answers] == [502, 502]
    assert app.state.d2m_breaker.current_state == "closed"
    assert app.state.atlas_breaker.current_state == "open"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-13"])
async def test__an_upstream_4xx_is_a_fact_not_an_outage(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The 404 between two outages is a fact: it resets the counter, the circuit stays closed (LM-13, LM-05)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=2)
    _statuses(upstream, [503, 404, 503])

    answers = await _ask(app, token(), 3)

    assert [answer.status_code for answer in answers] == [502, 204, 502]
    assert app.state.atlas_breaker.current_state == "closed"  # 3 failures only if the 404 counted
    assert app.state.atlas_breaker.fail_counter == 1


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-14"])
async def test__the_half_open_trial_closes_the_circuit_on_success(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The half-open trial reaches the upstream; its success closes the circuit (LM-14).

    The trial is driven through pybreaker's management API — the wall-clock
    reset timeout is the library's own tested behaviour; every transport here
    is a mock, so the app's half-open path is proven without sleeping.
    """
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=1)
    upstream.handler = lambda _request: httpx.Response(503)
    await _ask(app, token(), 1)
    app.state.atlas_breaker.half_open()
    _happy_upstream(upstream)

    answers = await _ask(app, token(), 1)

    assert [answer.status_code for answer in answers] == [200]
    assert answers[0].json() == EXTRACTED  # the answer is the chain's, unchanged (LM-01)
    assert app.state.atlas_breaker.current_state == "closed"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-14"])
async def test__the_half_open_trial_reopens_the_circuit_on_failure(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A failing trial is answered 502 and re-opens the circuit for its timeout (LM-14, LM-12)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=1)
    upstream.handler = lambda _request: httpx.Response(503)
    await _ask(app, token(), 1)
    app.state.atlas_breaker.half_open()

    answers = await _ask(app, token(), 1)

    assert [answer.status_code for answer in answers] == [502]
    assert app.state.atlas_breaker.current_state == "open"


# ---------------------------------------------------------------------------
# LM-07 (DV-22) — a transport failure is the app's 502, not a crash
# ---------------------------------------------------------------------------


def _refusing_upstream(upstream: FakeUpstream, path: str) -> None:
    """Answer every request to ``path`` with a refused connection, the rest as the happy chain (LM-07)."""
    refused = "connection refused"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == path:
            raise httpx.ConnectError(refused, request=request)
        if request.url.path == f"/v2/lineage/{E_IN}":
            return upstream.json(200, LINEAGE)
        return upstream.json(200, EXTRACTED)

    upstream.handler = handler


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__an_unreachable_atlas_is_a_502_not_a_crash(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The fetch's transport failure (connect refused) is the handler's 502 Atlas body (LM-07, DV-22)."""
    _refusing_upstream(upstream, f"/v2/lineage/{E_IN}")

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorMessage"] == "the lineage service is unreachable"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__an_unreachable_extract_is_a_502(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The extract leg's transport failure rides the same handler: 502, the fetch succeeded (LM-07, DV-22)."""
    _refusing_upstream(upstream, "/extract")

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorMessage"] == "the lineage service is unreachable"
    assert upstream.of(f"/v2/lineage/{E_IN}")  # the chain reached the extract leg


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__a_hanging_upstream_times_out_to_a_502(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A call that outlives UPSTREAM_TIMEOUT_SECONDS is a read timeout: a 502, never a hang (LM-07, LM-10).

    The MockTransport does not enforce the pool's timeout, so the handler raises
    what the bound raises at a real socket: the app's contract is the answer
    (502, DV-22), the bound's firing is httpx's tested behaviour.
    """
    timed_out = f"timed out after {UPSTREAM_TIMEOUT_SECONDS}s"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(timed_out, request=request)

    upstream.handler = handler

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorMessage"] == "the lineage service is unreachable"


# ---------------------------------------------------------------------------
# LM-12 / LM-13 — the extract side fast-fails; transport failures are outages
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-12"])
async def test__a_dead_extract_circuit_fast_fails_without_calling(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The open data2model circuit answers 502 FAST_FAIL_D2M with zero extract calls — the LM-12 mirror (LM-12)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=1)

    def tripping(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/extract":
            return httpx.Response(500)  # the extract outage: counted, trips its breaker (LM-13)
        return upstream.json(200, LINEAGE)

    upstream.handler = tripping
    await _ask(app, token(), 1)  # the trip
    assert app.state.d2m_breaker.current_state == "open"
    assert app.state.atlas_breaker.current_state == "closed"  # the fetch side is healthy (LM-11)

    upstream.requests.clear()
    answers = await _ask(app, token(), 3)

    assert [answer.status_code for answer in answers] == [502, 502, 502]
    assert answers[0].json()["errorMessage"] == FAST_FAIL_D2M
    assert upstream.of("/extract") == []  # the fast-fail: no extract call, no pool, no timeout


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-13"])
async def test__transport_failures_open_the_circuit(
    settings: Any,  # noqa: ANN401  # the fixture's settings object
    auth: Any,  # noqa: ANN401  # the fixture's verifier
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """Connect refused counts as an outage like a 5xx: two of them (fail_max=2) open the circuit (LM-13)."""
    app = _breaker_app(settings, auth, upstream, breaker_fail_max=2)

    refused = "connection refused"

    def refusing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(refused, request=request)

    upstream.handler = refusing

    answers = await _ask(app, token(), 2)

    assert [answer.status_code for answer in answers] == [502, 502]
    assert app.state.atlas_breaker.current_state == "open"

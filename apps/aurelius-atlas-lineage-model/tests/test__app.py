"""App-wiring tests: the endpoint contract, the auth gate, liveness (LM-01, LM-08, LM-09)."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from aurelius_atlas_lineage_model.app import create_app
from fake_upstream import FakeUpstream

# The lineage body: a dataset feeding a process feeding a dataset (LM-02 fixture).
LINEAGE: dict[str, Any] = {
    "guidEntityMap": {
        "e-in": {"guid": "e-in", "typeName": "kafka_topic", "displayText": "Ingest Topic"},
        "p-load": {"guid": "p-load", "typeName": "m4i_generic_process", "displayText": "Load Job"},
        "e-out": {"guid": "e-out", "typeName": "hive_table", "displayText": "Sales Table"},
    },
    "relations": [
        {"fromEntityId": "e-in", "relationshipId": "rel-1", "toEntityId": "p-load"},
        {"fromEntityId": "p-load", "relationshipId": "rel-2", "toEntityId": "e-out"},
    ],
}

# The data2model answer: the browser's document, returned verbatim (LM-01).
EXTRACTED: dict[str, Any] = {"model": '{"ar3_model": {"@identifier": "x"}}', "metadata": [{"id": "e-in", "data": {}}]}


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


def _happy_upstream(upstream: FakeUpstream) -> None:
    """Set the handler: the fetch answers the lineage, the extract answers the model body."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/lineage/e-in":
            return upstream.json(200, LINEAGE)
        return upstream.json(200, EXTRACTED)

    upstream.handler = handler


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-01"])
async def test__the_extract_body_is_returned_verbatim(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """200 application/json with the data2model body, byte for byte (the screen's document)."""
    _happy_upstream(upstream)

    response = await client.get("/", params={"guid": "e-in"}, headers=_bearer(token()))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == EXTRACTED
    assert response.json()["model"] == EXTRACTED["model"]  # the model stays a JSON string


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-08"])
async def test__a_missing_token_is_rejected(client: httpx.AsyncClient, upstream: FakeUpstream) -> None:
    """No bearer credential is a 401; no upstream call is made (AUX-05)."""
    _happy_upstream(upstream)

    response = await client.get("/", params={"guid": "e-in"})

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
    response = await client.get("/", params={"guid": "e-in"}, headers=_bearer(forged))

    assert response.status_code == 401
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-09"])
async def test__liveness_needs_no_token(client: httpx.AsyncClient) -> None:
    """The container healthcheck answers 204, anonymous."""
    response = await client.get("/liveness")

    assert response.status_code == 204


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-10"])
def test__the_app_is_built_from_the_settings(settings: Any) -> None:  # noqa: ANN401  # the fixture's settings object
    """The factory wires settings, auth and the upstream client onto the app state."""
    app = create_app(settings, http=httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500))))

    assert app.state.settings is settings
    assert app.title == "aurelius-atlas-lineage-model"
    assert app.docs_url is None  # an auxiliary API publishes no docs surface

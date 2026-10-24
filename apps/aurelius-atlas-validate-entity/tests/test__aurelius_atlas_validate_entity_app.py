"""App-wiring tests: the endpoint contract, the mock document, the auth gate, liveness (VE-01..VE-04)."""

from collections.abc import Callable

import httpx2 as httpx
import pytest
from aurelius_atlas_validate_entity.app import create_app
from aurelius_atlas_validate_entity.mock import MOCK_VALIDATION
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-01"])
async def test__the_mock_document_is_returned_verbatim(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """200 application/json with the mock document, byte for byte (VE-01, DV-50)."""
    entity = {"guid": "e-in", "typeName": "kafka_topic", "attributes": {"name": "Ingest Topic"}}

    response = await client.post("/", json=entity, headers=_bearer(token()))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == MOCK_VALIDATION


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-01"])
@pytest.mark.parametrize("body", [b"", b"not json {", b"{}", b'{"attributes": null}'])
async def test__any_body_is_accepted(client: httpx.AsyncClient, token: Callable[..., str], body: bytes) -> None:
    """The body is never read: malformed, empty and absent bodies all answer the mock (VE-01)."""
    response = await client.post(
        "/",
        content=body,
        headers={**_bearer(token()), "content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == MOCK_VALIDATION


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-02", "CL-07", "CL-50"])
def test__the_mock_document_is_the_legacy_output() -> None:
    """The legacy's ``output`` dict, key for key: four cards, one item each, canned verdicts (VE-02).

    The app's response is this constant validated through the client library's
    ``ValidationResponse`` — the app imports its own contract (CL-07), and the
    route answers its model_dump verbatim (CL-50).
    """
    assert list(MOCK_VALIDATION) == ["dataEntity", "definition", "domainLead", "name"]
    verdicts = {
        key: (card["items"][0]["result"]["raw"], card["items"][0]["compliant"]["raw"], card["isNonCompliant"])
        for key, card in MOCK_VALIDATION.items()
    }
    assert verdicts == {
        "dataEntity": ("This entity is missing a dataEntity", "0", True),
        "definition": ("This entity has a definition", "1", False),
        "domainLead": ("This entity is missing a domainLead", "0", True),
        "name": ("This entity has a name", "1", False),
    }
    for key, card in MOCK_VALIDATION.items():
        assert len(card["items"]) == 1
        item = card["items"][0]
        assert item["dataqualitytype"] == {"raw": "attribute"}
        assert item["usedattributes"] == {"raw": [key]}
        assert item["name"] == {"raw": f"Attribute - {key}"}
        assert item["_meta"]["engine"] == "atlas-dev-gov-quality"
        assert item["_meta"]["score"] == 1
        assert item["_meta"]["id"] == item["id"]["raw"]


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-03"])
async def test__a_missing_token_is_rejected(client: httpx.AsyncClient) -> None:
    """No bearer credential is a 401 (VE-03, DV-58) — the legacy's transparent auth accepted any."""
    response = await client.post("/", json={})

    assert response.status_code == 401


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-03"])
async def test__a_token_minted_for_another_audience_is_rejected(
    client: httpx.AsyncClient, token: Callable[..., str]
) -> None:
    """A token for a client outside the audience is a 401 (VE-03, AUX-04)."""
    forged = token(azp="some-other-client", audience="some-other-client")

    response = await client.post("/", json={}, headers=_bearer(forged))

    assert response.status_code == 401


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-04"])
async def test__liveness_needs_no_token(client: httpx.AsyncClient) -> None:
    """The container healthcheck answers 204, anonymous (VE-04, DV-59)."""
    response = await client.get("/liveness")

    assert response.status_code == 204


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-01"])
async def test__a_megabyte_body_still_answers_the_mock(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """The body is never read, so its size is not a constraint: a megabyte answers the mock (VE-01, DV-50)."""
    huge = b"[" + b'{"attribute": "x"},' * 30_000 + b"{}]"

    response = await client.post(
        "/",
        content=huge,
        headers={**_bearer(token()), "content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == MOCK_VALIDATION


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-01"])
async def test__a_body_without_a_content_type_still_answers_the_mock(
    client: httpx.AsyncClient, token: Callable[..., str]
) -> None:
    """A POST with no content-type answers the mock: the route reads no body, so the header is irrelevant (VE-01)."""
    response = await client.post("/", content=b"raw bytes, no declared type", headers=_bearer(token()))

    assert response.status_code == 200
    assert response.json() == MOCK_VALIDATION


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app")
async def test__the_mock_route_is_post_only(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """A GET on the mock route is a 405: the legacy endpoint is POST-only (DV-50).

    No rule states it — the framework does; the test names the route for ADR 049.
    """
    response = await client.get("/", headers=_bearer(token()))

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-05"])
def test__the_app_is_built_from_the_settings(settings: ValidateEntitySettings) -> None:
    """The factory wires the settings and the verifier onto the app state."""
    app = create_app(settings)

    assert app.state.settings is settings
    assert app.title == "aurelius-atlas-validate-entity"
    assert app.docs_url is None  # an auxiliary API publishes no docs surface

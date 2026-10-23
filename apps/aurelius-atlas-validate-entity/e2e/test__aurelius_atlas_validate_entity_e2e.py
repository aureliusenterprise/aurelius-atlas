"""E2E: the container image, Keycloak-minted tokens, real TLS (VE-01, VE-03, the 8.3 acceptance)."""

import httpx
import pytest
from aurelius_atlas_validate_entity.mock import MOCK_VALIDATION

# The editor's payload: an entity under edit, as the webapp's governance panel
# posts it (libs/atlas/api::GovQualityApi.validateEntity).
_ENTITY: dict[str, object] = {
    "guid": "6f1a2c34-0000-4000-8000-aureliusatlas0",
    "typeName": "m4i_data_table",
    "status": "ACTIVE",
    "attributes": {
        "name": "Sales Orders",
        "qualifiedName": "kafka.topic.sales_orders",
        "description": "Daily sales orders, ordered by region",
    },
}


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-03"])
async def test__a_missing_token_is_rejected(anonymous_client: httpx.AsyncClient) -> None:
    """The container, on the dev issuer: no bearer token is a 401 (VE-03, DV-24)."""
    response = await anonymous_client.post("/", json=_ENTITY)
    assert response.status_code == 401


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-01", "VE-03"])
async def test__the_mock_document_travels_over_https(client: httpx.AsyncClient) -> None:
    """With a real realm token, the entity in answers the mock document, byte for byte (VE-01)."""
    response = await client.post("/", json=_ENTITY)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == MOCK_VALIDATION


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-01"])
async def test__a_malformed_body_still_answers_the_mock(client: httpx.AsyncClient) -> None:
    """The body is never read: malformed JSON answers the mock too (VE-01, DV-14)."""
    response = await client.post(
        "/",
        content=b"not json {",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json() == MOCK_VALIDATION


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-04"])
async def test__liveness_answers_anonymously(anonymous_client: httpx.AsyncClient) -> None:
    """The container healthcheck route answers without a token (the image is healthy by construction)."""
    assert (await anonymous_client.get("/liveness")).status_code == 204

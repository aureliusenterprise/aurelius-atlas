"""Unit tests for the application: the body contract, auth, and validation (DTM-01, DTM-10, DTM-11)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_data2model.app import create_app
from aurelius_atlas_data2model.settings import Data2ModelSettings
from fastapi import FastAPI


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


# The lineage caller's payload, minimised: one edge, one static view (8.2).
_LINEAGE_BODY: dict[str, Any] = {
    "data": [
        {
            "id": "rel-1",
            "from_entity_id": "src",
            "from_entity_name": "Source",
            "from_entity_type": "kafka_topic",
            "from_process_id": None,
            "from_process_name": None,
            "from_process_type": None,
            "to_entity_id": None,
            "to_entity_name": None,
            "to_entity_type": None,
            "to_process_id": "proc",
            "to_process_name": "Process",
            "to_process_type": "m4i_generic_process",
        }
    ],
    "rules": {
        "elements": [
            {
                "id": "e-from-entity",
                "concept_type": "lineage_dataset",
                "id_key": "from_entity_id",
                "concept_name_key": "from_entity_name",
                "mapping": [{"key": "Type name", "value": "from_entity_type"}],
            },
            {
                "id": "e-to-process",
                "concept_type": "lineage_process",
                "id_key": "to_process_id",
                "concept_name_key": "to_process_name",
                "mapping": [{"key": "Type name", "value": "to_process_type"}],
            },
        ],
        "relations": [
            {
                "id": "r-1",
                "relationship_type": "lr",
                "id_key": "id",
                "source": "e-from-entity",
                "target": "e-to-process",
            }
        ],
        "views": [
            {
                "id": "v-1",
                "id_type": "static",
                "id_value": "lineage_view",
                "view_name_type": "static",
                "view_name_value": "Lineage",
                "view_layout": "archimate_process",
                "view_nodes": [{"rule": "e-from-entity"}, {"rule": "e-to-process"}],
                "view_edges": [],
            }
        ],
    },
}


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-01", "CL-07", "CL-50"])
async def test__extract_returns_metadata_and_an_ar3_model_string(
    client: httpx.AsyncClient,
    token: Callable[..., str],
) -> None:
    """200 with {metadata, model}: the model is a JSON string, content type application/json.

    The body is the client library's ``ExtractionResponse`` dumped whole — the app
    imports its own contract (CL-07) and answers its bytes verbatim, no
    ``response_model`` filtering (CL-50, the scenarios compare exact JSON).
    """
    response = await client.post("/extract", json=_LINEAGE_BODY, headers=_bearer(token()))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert set(body) == {"metadata", "model"}
    assert isinstance(body["model"], str)
    ar3 = json.loads(body["model"])
    assert ar3["ar3_model"]["@identifier"] == "Generated model"
    assert [entry["id"] for entry in body["metadata"]] == ["src", "proc", "rel-1", "lineage_view"]


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-10"])
async def test__liveness_needs_no_token(client: httpx.AsyncClient) -> None:
    """The healthcheck answers without a bearer token — the container probes it."""
    assert (await client.get("/liveness")).status_code == 204


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-10"])
async def test__a_missing_token_is_rejected(client: httpx.AsyncClient) -> None:
    """No authorization header is 401 (AUX-05)."""
    assert (await client.post("/extract", json=_LINEAGE_BODY)).status_code == 401


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-10"])
async def test__a_token_minted_for_another_audience_is_rejected(
    client: httpx.AsyncClient,
    token: Callable[..., str],
) -> None:
    """A token for the server's client id is not this app's audience (AUX-04)."""
    forged = token(azp="aurelius-atlas-server", audience="aurelius-atlas-server")
    assert (await client.post("/extract", json=_LINEAGE_BODY, headers=_bearer(forged))).status_code == 401


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-10"])
async def test__a_read_token_needs_no_write_role(app: FastAPI, token: Callable[..., str]) -> None:
    """/extract is read-only: a token with no roles at all passes (DTM-10)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://data2model") as reader:
        response = await reader.post("/extract", json={"data": [], "rules": {}}, headers=_bearer(token()))
    assert response.status_code == 200


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-11"])
async def test__a_malformed_body_is_rejected(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """A body that is not the request shape is a 400 with an Atlas-shaped error body."""
    response = await client.post("/extract", json={"data": "not rows"}, headers=_bearer(token()))
    assert response.status_code == 400
    body = response.json()
    assert body["errorCode"] == "ATLAS-400-00-029"
    assert "invalid extraction request" in body["errorMessage"]


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-11"])
async def test__an_unknown_concept_type_is_rejected(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """A concept type the type table does not know is a 400, not the legacy's 500."""
    body = {
        "data": [{"eid": "a"}],
        "rules": {
            "elements": [{"id": "e1", "concept_type": "not_a_type", "id_key": "eid"}],
            "relations": [],
            "views": [],
        },
    }
    assert (await client.post("/extract", json=body, headers=_bearer(token()))).status_code == 400


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-11"])
async def test__a_dangling_rule_reference_is_rejected(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """A relation naming an element rule that is not there is a 400 at parse time."""
    body = {
        "data": [],
        "rules": {
            "elements": [{"id": "e1", "concept_type": "lineage_dataset", "id_key": "eid"}],
            "relations": [{"id": "r1", "relationship_type": "lr", "id_key": "rid", "source": "e1", "target": "ghost"}],
            "views": [],
        },
    }
    assert (await client.post("/extract", json=body, headers=_bearer(token()))).status_code == 400


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-11"])
async def test__an_empty_body_yields_the_empty_model_skeleton(
    client: httpx.AsyncClient,
    token: Callable[..., str],
) -> None:
    """An empty body behaves as {data: [], rules: {}}: metadata [], the model skeleton."""
    response = await client.post("/extract", json={}, headers=_bearer(token()))
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"] == []
    ar3 = json.loads(body["model"])
    assert ar3["ar3_model"]["@identifier"] == "Generated model"
    assert ar3["ar3_model"]["ar3_elements"] == {"ar3_element": []}
    assert ar3["ar3_model"]["ar3_relationships"] == {"ar3_relationship": []}


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app")
def test__the_app_publishes_no_openapi_docs_or_redoc(settings: Data2ModelSettings, auth: KeycloakAuth) -> None:
    """The auxiliary API publishes no OpenAPI, docs, or redoc (DD-108, as the server)."""
    app = create_app(settings, auth=auth)
    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None

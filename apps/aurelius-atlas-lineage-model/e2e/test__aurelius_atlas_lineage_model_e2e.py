"""E2E: the 8.2 chain — the container, a Keycloak-minted token, the real data2model, the fixture Atlas.

The chain (DD-111): GET / fetches the canned graph from the fixture Atlas,
flattens it, and extracts the model through the real 8.1 data2model container,
forwarding the caller's bearer token (LM-04). The answer must equal the bytes
the scenario fixture carries — the 8.1 engine's own output for the same rows —
so the suite proves cross-container byte parity, not just a 200 (LM-01).
"""

import json
from pathlib import Path

import httpx
import pytest

CANNED_EXTRACT = Path(__file__).parents[1] / "scenarios" / "fixtures" / "graph.extract.json"
"""The 8.1 engine's answer for the canned graph's rows, generated with the fixtures."""


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-08"])
async def test__a_missing_token_is_rejected(anonymous_client: httpx.AsyncClient) -> None:
    """The container, on the dev issuer: no bearer token is a 401 (LM-08, AUX-05)."""
    response = await anonymous_client.get("/", params={"guid": "e-in"})
    assert response.status_code == 401


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-01", "LM-04", "LM-08"])
async def test__the_lineage_graph_extracts_through_the_chain(client: httpx.AsyncClient) -> None:
    """With a real realm token, the graph is fetched, flattened, and extracted by the real data2model (LM-01, LM-04)."""
    response = await client.get("/", params={"guid": "e-in"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    # The proxy answers the extraction verbatim: the same bytes the 8.1 engine
    # produces for the graph's rows (LM-01, proven against the 8.1 scenario).
    assert response.json() == json.loads(CANNED_EXTRACT.read_text())


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-05"])
async def test__an_unknown_guid_is_no_content(client: httpx.AsyncClient) -> None:
    """The fixture Atlas has no file for the guid: the upstream 404 becomes a 204 (LM-05)."""
    response = await client.get("/", params={"guid": "no-such-guid"})
    assert response.status_code == 204
    assert not response.content


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-09"])
async def test__liveness_answers_anonymously(anonymous_client: httpx.AsyncClient) -> None:
    """The container healthcheck route answers without a token (the image is healthy by construction)."""
    assert (await anonymous_client.get("/liveness")).status_code == 204

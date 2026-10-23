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
from aurelius_atlas_lineage_model_client import LineageModelClient

CANNED_EXTRACT = Path(__file__).parents[1] / "scenarios" / "fixtures" / "graph.extract.json"
"""The 8.1 engine's answer for the canned graph's rows, generated with the fixtures."""


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-08"])
async def test__a_missing_token_is_rejected(anonymous_client: httpx.AsyncClient) -> None:
    """The container, on the dev issuer: no bearer token is a 401 (LM-08, AUX-05)."""
    response = await anonymous_client.get("/", params={"guid": "e-in"})
    assert response.status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    rules=["LM-01", "LM-04", "LM-08", "CL-03", "CL-30"],
)
async def test__the_lineage_graph_extracts_through_the_chain(api: LineageModelClient) -> None:
    """With a real realm token, the client library runs the chain to the real data2model (LM-01, LM-04)."""
    response = await api.get("e-in")
    assert response is not None
    # The proxy answers the extraction verbatim: the same bytes the 8.1 engine
    # produces for the graph's rows (LM-01, proven against the 8.1 scenario).
    # The typed round-trip equals the fixture document, key for key.
    assert response.model_dump(mode="json", by_alias=True) == json.loads(CANNED_EXTRACT.read_text())


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    rules=["LM-05", "CL-30"],
)
async def test__an_unknown_guid_is_no_content(api: LineageModelClient) -> None:
    """The fixture Atlas has no file for the guid: the 204 becomes the client's ``None`` (LM-05, CL-30)."""
    assert await api.get("no-such-guid") is None


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-09"])
async def test__liveness_answers_anonymously(anonymous_client: httpx.AsyncClient) -> None:
    """The container healthcheck route answers without a token (the image is healthy by construction)."""
    assert (await anonymous_client.get("/liveness")).status_code == 204

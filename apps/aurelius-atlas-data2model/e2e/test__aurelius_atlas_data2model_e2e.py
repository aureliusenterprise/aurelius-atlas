"""E2E: the container image, Keycloak-minted tokens, real TLS (DTM-10, the 8.1 acceptance).

The happy path drives the container through the client library (CL-21): the
typed ``ExtractionRequest`` in, the typed ``ExtractionResponse`` out, over the
same TLS and the same minted token the raw tests use — the library is proven
against the real app, not a fake transport.
"""

import httpx2 as httpx
import pytest
from aurelius_atlas_data2model_client import Data2ModelClient, ExtractionRequest

# The lineage caller's payload (8.2), the same rules the parity scenario carries.
_LINEAGE_BODY: dict[str, object] = {
    "data": [
        {
            "id": "rel-1",
            "from_entity_id": "e-in",
            "from_entity_name": "Ingest Topic",
            "from_entity_type": "kafka_topic",
            "from_process_id": None,
            "from_process_name": None,
            "from_process_type": None,
            "to_entity_id": None,
            "to_entity_name": None,
            "to_entity_type": None,
            "to_process_id": "p-load",
            "to_process_name": "Load Job",
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


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app", rules=["DTM-10"])
async def test__a_missing_token_is_rejected(anonymous_client: httpx.AsyncClient) -> None:
    """The container, on the dev issuer: no bearer token is a 401 (DTM-10, AUX-05)."""
    response = await anonymous_client.post("/extract", json=_LINEAGE_BODY)
    assert response.status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_data2model.app.create_app",
    "aurelius_atlas_data2model_client.client.Data2ModelClient.extract",
    rules=["DTM-01", "DTM-10", "CL-03", "CL-21"],
)
async def test__the_lineage_rules_extract_over_https(api: Data2ModelClient) -> None:
    """With a real realm token, the client library extracts the diagram from the container (DTM-01, DTM-10)."""
    response = await api.extract(ExtractionRequest.model_validate(_LINEAGE_BODY))
    assert [entry.id for entry in response.metadata] == ["e-in", "p-load", "rel-1", "lineage_view"]
    assert response.model  # The ar3 JSON string the browser draws (DV-15).


@pytest.mark.covers("aurelius_atlas_data2model.app.create_app")
async def test__liveness_answers_anonymously(anonymous_client: httpx.AsyncClient) -> None:
    """The container healthcheck route answers without a token (the image is healthy by construction)."""
    assert (await anonymous_client.get("/liveness")).status_code == 204

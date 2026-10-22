"""The HTTP side of ``RelationshipREST`` (REL-03 to REL-08), on the fake Elasticsearch.

Read from ``RelationshipREST`` of Apache Atlas 2.4.0; the relationship rules themselves are tested on
``RelationshipStore`` in ``aurelius-atlas-core``.
"""

from typing import Any

import httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES

R = "aurelius_atlas_server.routes.relationship"
RELATIONSHIP = "/api/atlas/v2/relationship"


@pytest.fixture
async def ends(client: httpx.AsyncClient) -> dict[str, str]:
    """The sample types, a table and a database; their GUIDs by request GUID."""
    created = await client.post("/api/atlas/v2/types/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text
    entities = [
        {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}},
        {"typeName": "s_database", "guid": "-2", "attributes": {"qualifiedName": "d@cl"}},
    ]
    response = await client.post("/api/atlas/v2/entity/bulk", json={"entities": entities})
    return response.json()["guidAssignments"]


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and JSON body, or None for no body."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json() if response.content else None


@pytest.mark.covers(f"{R}.get_by_id", f"{R}.delete_by_id", rules=["REL-03"])
@pytest.mark.parametrize("method", ["GET", "DELETE"])
async def test__a_guid_over_4096_characters_is_refused(client: httpx.AsyncClient, method: str) -> None:
    """``Servlets.validateQueryParamLength`` runs first."""
    assert await send(client, method, f"{RELATIONSHIP}/guid/{'x' * 4097}") == (
        400,
        {"errorCode": "ATLAS-400-00-057", "errorMessage": "Length of query param guid exceeds the limit"},
    )


@pytest.mark.covers(
    f"{R}.create",
    f"{R}.update",
    f"{R}.get_by_id",
    f"{R}.delete_by_id",
    f"{R}.relationships",
    f"{R}.relationship_body",
    rules=["REL-04", "REL-05", "REL-06", "REL-07", "REL-08"],
)
async def test__a_relationship_is_created_read_updated_and_deleted(
    client: httpx.AsyncClient, ends: dict[str, str]
) -> None:
    """``POST``, ``GET`` with and without ``extendedInfo``, ``PUT`` and ``DELETE`` answering ``204``."""
    body = {"typeName": "s_table_home", "end1": {"guid": ends["-1"]}, "end2": {"guid": ends["-2"]}}

    status, created = await send(client, "POST", RELATIONSHIP, json=body)
    guid = created["guid"]
    _, plain = await send(client, "GET", f"{RELATIONSHIP}/guid/{guid}")
    _, extended = await send(client, "GET", f"{RELATIONSHIP}/guid/{guid}", params={"extendedInfo": "true"})
    _, updated = await send(client, "PUT", RELATIONSHIP, json={"guid": guid, "propagateTags": "NONE"})
    deleted = await send(client, "DELETE", f"{RELATIONSHIP}/guid/{guid}")

    assert (status, created["label"], created["status"]) == (200, "r:s_table_home", "ACTIVE")
    assert plain == {"relationship": created}
    assert sorted(extended["referredEntities"]) == sorted(ends.values())
    assert updated == created
    assert deleted == (204, None)
    assert (await send(client, "GET", f"{RELATIONSHIP}/guid/{guid}"))[1]["relationship"]["status"] == "DELETED"
    assert await send(client, "POST", RELATIONSHIP, content=b"") == (
        400,
        {"errorCode": "ATLAS-400-00-028", "errorMessage": "invalid value: unknown relationship type'null'"},
    )

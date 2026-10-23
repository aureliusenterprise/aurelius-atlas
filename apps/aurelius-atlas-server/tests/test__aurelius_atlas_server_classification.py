"""The classification endpoints of ``EntityREST`` (CLS-03 to CLS-09), on the fake Elasticsearch.

Read from ``EntityREST`` of Apache Atlas 2.4.0; the classification rules themselves are tested on
``EntityClassifications`` in ``aurelius-atlas-core``.
"""

from typing import Any

import httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import CLASSIFICATION_TYPES, SAMPLE_TYPES

E = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"


@pytest.fixture
async def table(client: httpx.AsyncClient) -> str:
    """The sample and classification types and a table ``t@cl``; its GUID."""
    for types in (SAMPLE_TYPES, CLASSIFICATION_TYPES):
        created = await client.post("/api/atlas/v2/types/typedefs", json=types)
        assert created.status_code == 200, created.text
    body = {"entities": [{"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}}]}
    response = await client.post(f"{ENTITY}/bulk", json=body)
    return response.json()["guidAssignments"]["-1"]


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and JSON body, or None for no body."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json() if response.content else None


UNIQUE = {"attr:qualifiedName": "t@cl"}


@pytest.mark.covers(
    f"{E}.add_classifications",
    f"{E}.get_classifications",
    f"{E}.get_classification",
    f"{E}.update_classifications",
    f"{E}.delete_classification",
    f"{E}.classifications_body",
    f"{E}.ensure_classification_type",
    rules=["CLS-03", "CLS-04", "CLS-05", "CLS-08", "CLS-09"],
)
async def test__classifications_are_added_read_updated_and_deleted_by_guid(
    client: httpx.AsyncClient, table: str
) -> None:
    """``204`` for the changes; the list as a ``PList``; unknown names and bodies that are no list fail."""
    added = await send(client, "POST", f"{ENTITY}/guid/{table}/classifications", json=[{"typeName": "c_pii"}])
    listed = await send(client, "GET", f"{ENTITY}/guid/{table}/classifications")
    updated = await send(
        client,
        "PUT",
        f"{ENTITY}/guid/{table}/classifications",
        json=[{"typeName": "c_pii", "attributes": {"level": 4}}],
    )
    one = await send(client, "GET", f"{ENTITY}/guid/{table}/classification/c_pii")
    unknown = await send(client, "GET", f"{ENTITY}/guid/{table}/classification/nope")
    not_a_list = await send(client, "POST", f"{ENTITY}/guid/{table}/classifications", json={"typeName": "c_pii"})
    deleted = await send(client, "DELETE", f"{ENTITY}/guid/{table}/classification/c_pii")

    assert (added, updated, deleted) == ((204, None), (204, None), (204, None))
    assert listed[1]["list"][0]["typeName"] == "c_pii"
    assert {key: listed[1][key] for key in ("startIndex", "pageSize", "totalCount", "sortType")} == {
        "startIndex": 0,
        "pageSize": 1,
        "totalCount": 1,
        "sortType": "NONE",
    }
    assert one[1]["attributes"]["level"] == 4
    assert unknown == (
        400,
        {"errorCode": "ATLAS-400-00-014", "errorMessage": "Type CLASSIFICATION with name nope does not exist"},
    )
    assert not_a_list[0] == 400
    assert (await send(client, "GET", f"{ENTITY}/guid/{table}/classifications"))[1]["list"] == []


@pytest.mark.covers(
    f"{E}.add_classifications_by_unique_attribute",
    f"{E}.update_classifications_by_unique_attribute",
    f"{E}.delete_classification_by_unique_attribute",
    f"{E}.guid_by_unique_attributes",
    rules=["CLS-06"],
)
async def test__the_unique_attribute_forms_find_the_entity_first(client: httpx.AsyncClient, table: str) -> None:
    """The same changes by ``attr:``; an unknown entity type or holder fails before them."""
    base = f"{ENTITY}/uniqueAttribute/type/s_table"
    added = await send(client, "POST", f"{base}/classifications", params=UNIQUE, json=[{"typeName": "c_pii"}])
    updated = await send(
        client, "PUT", f"{base}/classifications", params=UNIQUE, json=[{"typeName": "c_pii", "propagate": False}]
    )
    read = await send(client, "GET", f"{ENTITY}/guid/{table}/classification/c_pii")
    deleted = await send(client, "DELETE", f"{base}/classification/c_pii", params=UNIQUE)
    missing = await send(client, "POST", f"{base}/classifications", params={"attr:qualifiedName": "x"}, json=[])
    no_type = await send(client, "POST", f"{ENTITY}/uniqueAttribute/type/nope/classifications", json=[])

    assert (added, updated, deleted) == ((204, None), (204, None), (204, None))
    assert read[1]["propagate"] is False
    assert missing == (
        404,
        {
            "errorCode": "ATLAS-404-00-009",
            "errorMessage": "Instance s_table with unique attribute {qualifiedName=x} does not exist",
        },
    )
    assert no_type[0] == 400


@pytest.mark.covers(f"{E}.add_classification", rules=["CLS-07"])
async def test__one_classification_is_added_to_entities_by_guid_or_unique_attributes(
    client: httpx.AsyncClient, table: str
) -> None:
    """``bulk/classification``: its own parameter checks, then the add to each entity found."""
    bulk = f"{ENTITY}/bulk/classification"
    by_unique = {
        "classification": {"typeName": "c_pii"},
        "entityTypeName": "s_table",
        "entitiesUniqueAttributes": [{"qualifiedName": "t@cl"}, {"qualifiedName": "nobody"}],
    }

    assert await send(client, "POST", bulk, json={"entityGuids": [table]}) == (
        400,
        {"errorCode": "ATLAS-400-00-01A", "errorMessage": "invalid parameters: no classification"},
    )
    assert (await send(client, "POST", bulk, json={"classification": {"typeName": "c_pii"}}))[1]["errorMessage"] == (
        "invalid parameters: Need either list of GUIDs or entity type and list of qualified Names"
    )
    assert (await send(client, "POST", bulk, json={**by_unique, "entitiesUniqueAttributes": [{"qualifiedName": "x"}]}))[
        1
    ]["errorMessage"] == "invalid parameters: No guid found for given entity Type Name and list of attributes"
    assert await send(client, "POST", bulk, json=by_unique) == (204, None)
    assert await send(
        client, "POST", bulk, json={"classification": {"typeName": "c_secret"}, "entityGuids": [table]}
    ) == (
        204,
        None,
    )
    names = (await send(client, "GET", f"{ENTITY}/guid/{table}/header"))[1]["classificationNames"]
    assert names == ["c_pii", "c_secret"]

"""The HTTP side of the entity writes of ``EntityREST`` (EWR-01 to EWR-16).

Read from ``EntityREST`` and ``AtlasEntityStoreV2`` of Apache Atlas 2.4.0 and its test ``EntityV2JerseyResourceIT``;
the write rules themselves are tested on ``EntityWriter`` in ``aurelius-atlas-core``.
"""

from typing import Any

import httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES, WRITE_TYPES

E = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"
JSON = "application/json; charset=UTF-8"


@pytest.fixture
async def typed(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """The client of a server holding the sample and write types."""
    for types in (SAMPLE_TYPES, WRITE_TYPES):
        created = await client.post("/api/atlas/v2/types/typedefs", json=types)
        assert created.status_code == 200, created.text
    return client


async def send(client: httpx.AsyncClient, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and JSON body of a request, which must be Atlas JSON."""
    response = await client.request(method, f"{ENTITY}{path}", **kwargs)
    assert response.headers["content-type"] == JSON
    return response.status_code, response.json()


def error(code: str, message: str) -> dict[str, str]:
    """Atlas's error body."""
    return {"errorCode": code, "errorMessage": message}


@pytest.mark.covers(
    f"{E}.partial_update_entity_by_unique_attrs", f"{E}.partial_update_entity_attr_by_guid", rules=["EWR-01"]
)
@pytest.mark.parametrize(
    ("path", "param"),
    [
        ("/uniqueAttribute/type/{}", "typeName"),
        ("/guid/{}", "guid"),
        ("/guid/g?name={}", "name"),
    ],
)
async def test__a_type_name_guid_or_name_over_4096_characters_is_refused(
    client: httpx.AsyncClient, path: str, param: str
) -> None:
    """``Servlets.validateQueryParamLength`` runs before anything is read."""
    assert await send(client, "PUT", path.format("x" * 4097), json="v") == (
        400,
        error("ATLAS-400-00-057", f"Length of query param {param} exceeds the limit"),
    )


@pytest.mark.covers(f"{E}.create_or_update", f"{E}.json_body", f"{E}.model_body", rules=["EWR-02", "EWR-13"])
async def test__an_entity_is_created_then_read_back(typed: httpx.AsyncClient) -> None:
    """``POST /``: the mutation response names the new GUID; the entity reads back as stored."""
    body = {"entity": {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl", "sizes": [1.50]}}}

    status, created = await send(typed, "POST", "", json=body)
    guid = created["guidAssignments"]["-1"]
    _, read = await send(typed, "GET", f"/guid/{guid}")

    assert status == 200
    assert created["mutatedEntities"]["CREATE"][0]["guid"] == guid
    assert read["entity"]["attributes"]["sizes"] == [1]


@pytest.mark.covers(
    f"{E}.create_or_update", f"{E}.create_or_update_bulk", f"{E}.json_body", f"{E}.model_body", rules=["EWR-02"]
)
async def test__a_request_without_entities_or_with_a_bad_body_fails(typed: httpx.AsyncClient) -> None:
    """No entity: ``INVALID_PARAMETERS``; a body that is not JSON or not the model: ``BAD_REQUEST`` (DV-10)."""
    assert await send(typed, "POST", "", content=b"") == (
        400,
        error("ATLAS-400-00-01A", "invalid parameters: found null entity"),
    )
    assert await send(typed, "POST", "/bulk", json={}) == (
        400,
        error("ATLAS-400-00-01A", "invalid parameters: no entities to create/update."),
    )
    status, bad = await send(typed, "POST", "/bulk", content=b"{")
    assert (status, bad["errorCode"]) == (400, "ATLAS-400-00-029")
    status, bad = await send(typed, "POST", "/bulk", json={"entities": 5})
    assert (status, bad["errorCode"]) == (400, "ATLAS-400-00-029")
    assert bad["errorMessage"].startswith("Invalid AtlasEntitiesWithExtInfo: ")


@pytest.mark.covers(
    f"{E}.create_or_update_bulk", f"{E}.partial_update_entity_by_unique_attrs", rules=["EWR-13", "EWR-14"]
)
async def test__entities_are_created_in_bulk_and_updated_by_unique_attributes(typed: httpx.AsyncClient) -> None:
    """``POST bulk`` creates both; ``PUT uniqueAttribute`` answers ``PARTIAL_UPDATE`` and checks its input."""
    entities = [
        {"typeName": "s_database", "guid": "-1", "attributes": {"qualifiedName": "db@cl"}},
        {"typeName": "s_table", "guid": "-2", "attributes": {"qualifiedName": "t@cl", "db": {"guid": "-1"}}},
    ]
    path = "/uniqueAttribute/type/s_table"

    _, created = await send(typed, "POST", "/bulk", json={"entities": entities})
    status, updated = await send(
        typed,
        "PUT",
        path,
        params={"attr:qualifiedName": "t@cl"},
        json={"entity": {"typeName": "s_table", "attributes": {"name": "n"}}},
    )

    assert list(created["guidAssignments"]) == ["-1", "-2"]
    assert len(created["mutatedEntities"]["CREATE"]) == 2
    assert status == 200
    assert updated["partialUpdatedEntities"][0]["attributes"]["name"] == "n"
    assert await send(typed, "PUT", path, params={"attr:qualifiedName": "t@cl"}, content=b"") == (
        400,
        error("ATLAS-400-00-01A", "invalid parameters: no entity to update."),
    )
    assert await send(
        typed, "PUT", path, params={"attr:qualifiedName": "x"}, json={"entity": {"typeName": "s_table"}}
    ) == (
        404,
        error("ATLAS-404-00-009", "Instance s_table with unique attribute {qualifiedName=x} does not exist"),
    )
    assert await send(typed, "PUT", path, params={"attr:name": "n"}, json={}) == (
        400,
        error("ATLAS-400-00-013", "Type s_table with unique attribute name does not exist"),
    )


@pytest.mark.covers(f"{E}.partial_update_entity_attr_by_guid", rules=["EWR-15"])
async def test__one_attribute_is_set_by_guid(typed: httpx.AsyncClient) -> None:
    """``PUT guid/{guid}?name=``: the body is the value; an unknown attribute fails."""
    _, created = await send(
        typed,
        "POST",
        "",
        json={"entity": {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}}},
    )
    guid = created["guidAssignments"]["-1"]

    status, updated = await send(typed, "PUT", f"/guid/{guid}", params={"name": "name"}, json="orders")

    assert (status, updated["mutatedEntities"]["PARTIAL_UPDATE"][0]["displayText"]) == (200, "orders")
    assert await send(typed, "PUT", f"/guid/{guid}", params={"name": "nothing"}, json=1) == (
        400,
        error("ATLAS-400-00-023", "Attribute nothing not found for type s_table"),
    )

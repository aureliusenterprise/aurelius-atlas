"""The basic search endpoints of ``DiscoveryREST`` (SRC-02, SRC-09, SRC-11), on the fake Elasticsearch.

Read from ``DiscoveryREST`` of Apache Atlas 2.4.0; the search itself is tested on ``EntityDiscoveryService`` in
``aurelius-atlas-core``.
"""

from typing import Any

import httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES

D = "aurelius_atlas_server.routes.discovery"
E = "aurelius_atlas_server.routes.entity"
SEARCH = "/api/atlas/v2/search"


@pytest.fixture
async def tables(client: httpx.AsyncClient) -> list[str]:
    """The sample types and tables ``t1@se`` to ``t3@se``, named ``one`` to ``three``; their GUIDs."""
    created = await client.post("/api/atlas/v2/types/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text
    entities = [
        {"typeName": "s_table", "guid": f"-{n}", "attributes": {"qualifiedName": f"t{n}@se", "name": name}}
        for n, name in ((1, "one"), (2, "two"), (3, "three"))
    ]
    response = await client.post("/api/atlas/v2/entity/bulk", json={"entities": entities})
    return [response.json()["guidAssignments"][f"-{n}"] for n in (1, 2, 3)]


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and the JSON body."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json()


def names(body: dict[str, Any]) -> list[str]:
    """The names of the entities found."""
    return sorted(entity["attributes"]["name"] for entity in body.get("entities", []))


@pytest.mark.covers(f"{D}.search_with_parameters", f"{D}.validate_basic_search_parameters", rules=["SRC-02", "SRC-09"])
async def test__a_posted_search_is_validated_then_answered(client: httpx.AsyncClient, tables: list[str]) -> None:
    """An entity filter finds its table; each invalid body fails with Atlas's message."""
    status, found = await send(
        client,
        "POST",
        f"{SEARCH}/basic",
        json={
            "typeName": "s_table",
            "entityFilters": {"attributeName": "name", "operator": "=", "attributeValue": "two"},
        },
    )
    invalid = [
        ({"typeName": "s_table", "limit": -1}, "Limit/offset should be non-negative"),
        (
            {"entityFilters": {"attributeName": "name", "operator": "=", "attributeValue": "x"}},
            "EntityFilters specified without Type name",
        ),
        ({"typeName": "s_table", "tagFilters": {"attributeName": "x"}}, "TagFilters specified without tag name"),
        (
            {},
            (
                "No search parameter was found. One of the following MUST be specified in the request; typeName, "
                "classification, termName or queryText"
            ),
        ),
        ({"typeName": "x" * 4097}, "Length of query param typeName exceeds the limit"),
    ]
    messages = [(await send(client, "POST", f"{SEARCH}/basic", json=body))[1]["errorMessage"] for body, _ in invalid]

    assert (status, names(found), found["approximateCount"]) == (200, ["two"], 1)
    assert found["entities"][0]["guid"] == tables[1]
    assert messages == [expected for _, expected in invalid]


@pytest.mark.covers(
    f"{D}.search_using_basic",
    f"{E}.first_value",
    f"{E}.java_number",
    f"{E}.parsed_value",
    rules=["SRC-11"],
)
async def test__a_basic_search_by_query_parameters(client: httpx.AsyncClient, tables: list[str]) -> None:
    """Sorted and paged by parameters, unvalidated; a parameter of the wrong type is a bad request (DV-39)."""
    status, page = await send(
        client,
        "GET",
        f"{SEARCH}/basic",
        params={"typeName": "s_table", "sortBy": "name", "sortOrder": "DESCENDING", "limit": "2", "offset": "-5"},
    )
    deleted = await client.delete(f"/api/atlas/v2/entity/guid/{tables[0]}")
    _, active = await send(
        client, "GET", f"{SEARCH}/basic", params={"typeName": "s_table", "excludeDeletedEntities": "TRUE"}
    )
    bad_order = await send(client, "GET", f"{SEARCH}/basic", params={"typeName": "s_table", "sortOrder": "down"})
    bad_limit = await send(client, "GET", f"{SEARCH}/basic", params={"typeName": "s_table", "limit": "many"})
    nothing = await send(client, "GET", f"{SEARCH}/basic")

    assert status == 200
    assert [entity["attributes"]["name"] for entity in page["entities"]] == ["two", "three"]
    assert (page["searchParameters"]["limit"], page["searchParameters"]["offset"]) == (2, 0)
    assert deleted.status_code == 200
    assert names(active) == ["three", "two"]
    assert bad_order == (
        400,
        {"errorCode": "ATLAS-400-00-029", "errorMessage": "Invalid value down for query parameter sortOrder"},
    )
    assert bad_limit[0] == 400
    assert nothing[1]["errorCode"] == "ATLAS-400-00-047"


@pytest.mark.covers(f"{D}.search_using_attribute", rules=["SRC-11"])
async def test__an_attribute_search_finds_values_by_prefix(client: httpx.AsyncClient, tables: list[str]) -> None:
    """By the attribute named, by ``qualifiedName`` by default; neither name nor prefix, or no type, fails."""
    _, by_name = await send(
        client, "GET", f"{SEARCH}/attribute", params={"attrName": "name", "attrValuePrefix": "t", "typeName": "s_table"}
    )
    _, by_default = await send(
        client, "GET", f"{SEARCH}/attribute", params={"attrValuePrefix": "t1@", "typeName": "s_table"}
    )
    _, unknown_type = await send(
        client, "GET", f"{SEARCH}/attribute", params={"attrValuePrefix": "t", "typeName": "nope"}
    )
    neither = await send(client, "GET", f"{SEARCH}/attribute")
    untyped = await send(client, "GET", f"{SEARCH}/attribute", params={"attrValuePrefix": "t"})

    assert names(by_name) == ["three", "two"]
    assert names(by_default) == ["one"]
    assert unknown_type["errorMessage"] == "nope: Unknown/invalid typename"
    assert neither == (
        400,
        {
            "errorCode": "ATLAS-400-00-01A",
            "errorMessage": "invalid parameters: attrName : null, attrValue: null for attribute search.",
        },
    )
    assert untyped[1]["errorMessage"] == "EntityFilters specified without Type name"
    assert tables

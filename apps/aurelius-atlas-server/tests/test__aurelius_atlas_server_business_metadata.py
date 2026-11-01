"""The business metadata endpoints (BMD-01 to BMD-06, AUZ-17) of ``EntityREST``, as Apache Atlas 2.4.0 serves them."""

from typing import Any

import httpx2 as httpx
import pytest
from fake_issuer import FakeIssuer

R = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"
ON = '["t_bmd"]'
TYPES = {
    "entityDefs": [
        {
            "name": "t_bmd",
            "superTypes": [],
            "attributeDefs": [{"name": "qualifiedName", "typeName": "string", "isUnique": True, "isOptional": False}],
        }
    ],
    "businessMetadataDefs": [
        {
            "name": "bm_a",
            "attributeDefs": [
                {
                    "name": "s",
                    "typeName": "string",
                    "isOptional": True,
                    "options": {"applicableEntityTypes": ON, "maxStrLength": "20"},
                },
                {"name": "n", "typeName": "int", "isOptional": True, "options": {"applicableEntityTypes": ON}},
            ],
        }
    ],
}


async def entity(client: httpx.AsyncClient, **business: Any) -> str:  # noqa: ANN401 - attribute values
    """The GUID of a new ``t_bmd`` of these business attributes."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    body = {"entity": {"typeName": "t_bmd", "attributes": {"qualifiedName": "q"}, "businessAttributes": business}}
    created = (await client.post(ENTITY, json=body)).json()
    return str(created["mutatedEntities"]["CREATE"][0]["guid"])


async def business(client: httpx.AsyncClient, guid: str) -> dict[str, Any] | None:
    """The entity's business attributes as its read answers them."""
    return (await client.get(f"{ENTITY}/guid/{guid}")).json()["entity"].get("businessAttributes")


@pytest.mark.covers(
    f"{R}.business_metadata",
    f"{R}.business_attributes_body",
    f"{R}.attributes_body",
    f"{R}.add_or_update_business_attributes",
    f"{R}.remove_business_attributes",
    f"{R}.add_or_update_business_attributes_of",
    f"{R}.remove_business_attributes_of",
    rules=["BMD-01", "BMD-02", "BMD-03", "BMD-04", "BMD-05", "BMD-06"],
)
async def test__business_attributes_are_set_and_removed(client: httpx.AsyncClient) -> None:
    """Each endpoint answers 204 without a body; the entity reads them back, and the audit tells each change."""
    guid = await entity(client, bm_a={"s": "x"})
    url = f"{ENTITY}/guid/{guid}/businessmetadata"
    assert await business(client, guid) == {"bm_a": {"s": "x"}}

    added = await client.post(f"{url}/bm_a", json={"n": 1})
    assert (added.status_code, added.content) == (204, b"")
    assert await business(client, guid) == {"bm_a": {"s": "x", "n": 1}}
    assert (await client.post(url, params={"isOverwrite": "true"}, json={"bm_a": {"n": 2}})).status_code == 204
    assert await business(client, guid) == {"bm_a": {"n": 2}}
    assert (await client.post(url, json={"bm_a": {"s": "y"}})).status_code == 204
    assert (await client.request("DELETE", url, json={"bm_a": {"n": None}})).status_code == 204
    assert await business(client, guid) == {"bm_a": {"s": "y"}}
    assert (await client.request("DELETE", f"{url}/bm_a")).status_code == 204
    assert await business(client, guid) is None
    audit = (await client.get(f"{ENTITY}/{guid}/audit")).json()
    details = [event["details"] for event in audit if event["action"] == "BUSINESS_ATTRIBUTE_UPDATE"]
    assert details[0] == 'Updated business attributes: {"typeName":"bm_a","attributes":{"s":null,"n":null}}'
    assert len(details) == 6


@pytest.mark.covers(f"{R}.business_attributes_body", f"{R}.attributes_body", rules=["BMD-01"])
async def test__a_body_that_is_no_map_of_values_is_refused(client: httpx.AsyncClient) -> None:
    """``BAD_REQUEST`` (DV-10); an empty map is ``INVALID_PARAMETERS``; an invalid value every message."""
    guid = await entity(client)
    url = f"{ENTITY}/guid/{guid}/businessmetadata"
    for body in (["a"], {"bm_a": 1}, "a"):
        assert (await client.post(url, json=body)).status_code == 400
    assert (await client.post(f"{url}/bm_a", json=["a"])).status_code == 400
    empty = await client.post(url, json={})
    assert empty.json()["errorMessage"] == "invalid parameters: businessAttributes is null/empty"
    invalid = await client.post(url, json={"bm_a": {"s": "x" * 21}, "nope": {}})
    assert (invalid.status_code, invalid.json()["errorCode"]) == (404, "ATLAS-404-00-007")
    assert (await client.post(f"{ENTITY}/guid/missing/businessmetadata", json={"bm_a": {}})).status_code == 404


@pytest.mark.covers(f"{R}.business_metadata", rules=["AUZ-17"])
async def test__a_reader_changes_no_business_attributes(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``atlas-read`` may not update or remove business metadata; nothing changes."""
    guid = await entity(client, bm_a={"n": 1})
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}
    url = f"{ENTITY}/guid/{guid}/businessmetadata"

    refused = await client.post(f"{url}/bm_a", json={"n": 2}, headers=reader)
    assert (refused.status_code, refused.json()["errorMessage"]) == (
        403,
        f"reader is not authorized to perform add/update business-metadata: guid={guid}, business-metadata-name=bm_a",
    )
    removed = await client.request("DELETE", url, json={"bm_a": None}, headers=reader)
    assert removed.json()["errorMessage"] == (
        f"reader is not authorized to perform remove business-metadata: guid={guid}, business-metadata=bm_a"
    )
    assert await business(client, guid) == {"bm_a": {"n": 1}}

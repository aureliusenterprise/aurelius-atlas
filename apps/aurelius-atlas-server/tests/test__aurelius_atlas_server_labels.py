"""The label endpoints (LBL-01 to LBL-05, AUZ-16) of ``EntityREST``, as Apache Atlas 2.4.0 serves them."""

import httpx2 as httpx
import pytest
from fake_issuer import FakeIssuer

R = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"
TYPES = {
    "entityDefs": [
        {
            "name": "t_lbl",
            "superTypes": [],
            "attributeDefs": [
                {"name": "qualifiedName", "typeName": "string", "isUnique": True, "isOptional": False},
            ],
        }
    ]
}
UNIQUE = f"{ENTITY}/uniqueAttribute/type/t_lbl/labels?attr:qualifiedName=q1"


async def entity(client: httpx.AsyncClient, *labels: str) -> str:
    """The GUID of a new ``t_lbl`` ``q1`` of these labels."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    body = {"entity": {"typeName": "t_lbl", "attributes": {"qualifiedName": "q1"}, "labels": list(labels)}}
    created = (await client.post(ENTITY, json=body)).json()
    return str(created["mutatedEntities"]["CREATE"][0]["guid"])


async def labels_of(client: httpx.AsyncClient, guid: str) -> list[str]:
    """The entity's labels as its header answers them."""
    return (await client.get(f"{ENTITY}/guid/{guid}/header")).json()["labels"]


@pytest.mark.covers(
    f"{R}.labels",
    f"{R}.labels_body",
    f"{R}.set_labels",
    f"{R}.add_labels",
    f"{R}.remove_labels",
    rules=["LBL-01", "LBL-02", "LBL-03", "LBL-04", "LBL-05"],
)
async def test__labels_are_set_added_and_removed_by_guid(client: httpx.AsyncClient) -> None:
    """Each answers 204 without a body; the audit tells what each changed."""
    guid = await entity(client, "a")
    url = f"{ENTITY}/guid/{guid}/labels"

    added = await client.put(url, json=["b", "c"])
    assert (added.status_code, added.content) == (204, b"")
    assert await labels_of(client, guid) == ["a", "b", "c"]
    assert (await client.request("DELETE", url, json=["a"])).status_code == 204
    assert await labels_of(client, guid) == ["b", "c"]
    assert (await client.post(url, json=["d"])).status_code == 204
    assert await labels_of(client, guid) == ["d"]
    assert (await client.post(url)).status_code == 204
    assert await labels_of(client, guid) == []
    audit = (await client.get(f"{ENTITY}/{guid}/audit")).json()
    # one request's events may share a millisecond, so their order is not compared (LBL-05's order: core tests)
    assert sorted((event["action"], event["details"]) for event in audit if event["action"].startswith("LABEL")) == [
        ("LABEL_ADD", "Added labels: a"),
        ("LABEL_ADD", "Added labels: b c"),
        ("LABEL_ADD", "Added labels: d"),
        ("LABEL_DELETE", "Deleted labels: a"),
        ("LABEL_DELETE", "Deleted labels: b c"),
        ("LABEL_DELETE", "Deleted labels: d"),
    ]


@pytest.mark.covers(
    f"{R}.set_labels_by_unique_attribute",
    f"{R}.add_labels_by_unique_attribute",
    f"{R}.remove_labels_by_unique_attribute",
    rules=["LBL-01"],
)
async def test__labels_are_changed_by_unique_attributes(client: httpx.AsyncClient) -> None:
    """The entity holding the ``attr:`` values; an unknown type or entity fails first."""
    guid = await entity(client)

    assert (await client.put(UNIQUE, json=["a", "b"])).status_code == 204
    assert (await client.request("DELETE", UNIQUE, json=["b"])).status_code == 204
    assert await labels_of(client, guid) == ["a"]
    assert (await client.post(UNIQUE, json=["c"])).status_code == 204
    assert await labels_of(client, guid) == ["c"]
    missing = await client.post(UNIQUE.replace("q1", "q2"), json=["c"])
    assert (missing.status_code, missing.json()["errorCode"]) == (404, "ATLAS-404-00-009")
    unknown = await client.put(f"{ENTITY}/uniqueAttribute/type/nope/labels?attr:qualifiedName=q1", json=["c"])
    assert (unknown.status_code, unknown.json()["errorCode"]) == (400, "ATLAS-400-00-014")


@pytest.mark.covers(f"{R}.labels_body", rules=["LBL-01"])
async def test__a_body_that_is_no_array_of_labels_is_refused(client: httpx.AsyncClient) -> None:
    """``BAD_REQUEST`` (DV-10); an empty array to add is ``INVALID_PARAMETERS``."""
    guid = await entity(client)
    url = f"{ENTITY}/guid/{guid}/labels"
    for body in ({"a": 1}, ["a", 1], "a"):
        assert (await client.put(url, json=body)).status_code == 400
    empty = await client.put(url, json=[])
    assert (empty.status_code, empty.json()["errorMessage"]) == (400, "invalid parameters: labels is null/empty")
    assert (await client.post(f"{ENTITY}/guid/nope/labels", json=["a"])).status_code == 404


@pytest.mark.covers(f"{R}.labels", rules=["AUZ-16"])
async def test__a_reader_changes_no_labels(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``atlas-read`` may not add or remove a label; nothing changes."""
    guid = await entity(client, "a")
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}

    refused = await client.put(f"{ENTITY}/guid/{guid}/labels", json=["b"], headers=reader)
    assert (refused.status_code, refused.json()["errorMessage"]) == (
        403,
        f"reader is not authorized to perform add/update label: guid={guid}, label=b",
    )
    removed = await client.request("DELETE", UNIQUE, json=["a"], headers=reader)
    assert removed.json()["errorMessage"] == f"reader is not authorized to perform remove label: guid={guid}, label=a"
    assert await labels_of(client, guid) == ["a"]

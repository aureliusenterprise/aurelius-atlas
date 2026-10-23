"""``getAuditEvents`` of ``EntityREST`` (AUD-06 to AUD-09), on the fake Elasticsearch.

Read from ``EntityREST#getAuditEvents`` of Apache Atlas 2.4.0; the events themselves are tested on the listener
and the repository in ``aurelius-atlas-core``.
"""

from typing import Any

import httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES

E = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"


@pytest.fixture
async def table(client: httpx.AsyncClient) -> str:
    """The sample types and a table ``t@au`` created, then updated twice; its GUID."""
    created = await client.post("/api/atlas/v2/types/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text
    body: dict[str, Any] = {"entity": {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@au"}}}
    guid = (await client.post(ENTITY, json=body)).json()["guidAssignments"]["-1"]
    for name in ("one", "two"):
        await client.put(f"{ENTITY}/guid/{guid}", params={"name": "name"}, json=name)
    return guid


async def actions(client: httpx.AsyncClient, guid: str, **params: str) -> tuple[int, Any]:
    """The status, and the actions listed or the error body."""
    response = await client.get(f"{ENTITY}/{guid}/audit", params=params)
    body = response.json()
    return response.status_code, [event["action"] for event in body] if response.status_code == 200 else body


@pytest.mark.covers(f"{E}.get_audit_events", rules=["AUD-07", "AUD-08", "AUD-09"])
async def test__events_are_paged_by_start_key_or_sorted_and_filtered(client: httpx.AsyncClient, table: str) -> None:
    """Newest first from a key, that one again; by action and its ``TAG_`` alias; sorted descending by action."""
    first = (await client.get(f"{ENTITY}/{table}/audit", params={"count": "2"})).json()
    rest = await actions(client, table, startKey=first[1]["eventKey"], count="5")

    assert [event["action"] for event in first] == ["ENTITY_UPDATE", "ENTITY_UPDATE"]
    assert rest == (200, ["ENTITY_UPDATE", "ENTITY_CREATE"])
    assert await actions(client, table, auditAction="ENTITY_CREATE") == (200, ["ENTITY_CREATE"])
    assert await actions(client, table, auditAction="TAG_ADD") == (200, [])
    assert await actions(client, table, sortBy="action", sortOrder="DESC") == (
        200,
        ["ENTITY_UPDATE", "ENTITY_UPDATE", "ENTITY_CREATE"],
    )
    assert await actions(client, table, offset="2", count="-1") == (200, ["ENTITY_UPDATE"])
    assert await actions(client, table, count="-1", startKey=first[0]["eventKey"]) == (
        200,
        ["ENTITY_UPDATE", "ENTITY_UPDATE", "ENTITY_CREATE"],
    )


@pytest.mark.covers(f"{E}.get_audit_events", rules=["AUD-09"])
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("count", "many"),
        ("count", "40000"),
        ("count", " 5"),
        ("offset", "x"),
        ("auditAction", "CUSTOM_ATTRIBUTE_UPDATE"),
    ],
)
async def test__a_parameter_that_is_no_value_of_its_type_is_a_bad_request(
    client: httpx.AsyncClient, table: str, name: str, value: str
) -> None:
    """``BAD_REQUEST`` naming the value and the parameter, where Atlas answers a ``500`` (DV-39)."""
    assert await actions(client, table, **{name: value}) == (
        400,
        {"errorCode": "ATLAS-400-00-029", "errorMessage": f"Invalid value {value} for query parameter {name}"},
    )


@pytest.mark.covers(f"{E}.get_audit_events", f"{E}.notifier", f"{E}.writer", rules=["AUD-03", "AUD-06"])
async def test__a_purged_entity_keeps_its_audit_and_an_unknown_one_has_none(
    client: httpx.AsyncClient, table: str
) -> None:
    """After delete and purge the events stay readable, the purge first; a GUID never used is not found."""
    await client.delete(f"{ENTITY}/guid/{table}")
    purged = await client.put("/api/atlas/admin/purge", json=[table])

    status, listed = await actions(client, table)

    assert purged.status_code == 200
    assert (status, listed[:2]) == (200, ["ENTITY_PURGE", "ENTITY_DELETE"])
    assert (await actions(client, "nope"))[1]["errorCode"] == "ATLAS-404-00-005"


@pytest.mark.covers(f"{E}.get_entity_headers", f"{E}.classifications", rules=["CAU-02", "CAU-07", "CAU-08"])
async def test__entities_whose_classifications_changed_are_listed_with_their_headers(
    client: httpx.AsyncClient, table: str
) -> None:
    """An added classification is audited and lists its entity; a start after now or no number is a bad request."""
    created = await client.post("/api/atlas/v2/types/typedefs", json={"classificationDefs": [{"name": "c_au"}]})
    added = await client.post(f"{ENTITY}/guid/{table}/classifications", json=[{"typeName": "c_au"}])

    audited = await actions(client, table, auditAction="CLASSIFICATION_ADD")
    headers = await client.get(f"{ENTITY}/bulk/headers", params={"tagUpdateStartTime": "0"})
    none = await client.get(f"{ENTITY}/bulk/headers")
    future = await client.get(f"{ENTITY}/bulk/headers", params={"tagUpdateStartTime": str(2**62)})
    text = await client.get(f"{ENTITY}/bulk/headers", params={"tagUpdateStartTime": "soon"})

    assert (created.status_code, added.status_code) == (200, 204)
    assert audited == (200, ["CLASSIFICATION_ADD"])
    header = headers.json()["guidHeaderMap"][table]
    assert [c["typeName"] for c in header["classifications"]] == ["c_au"]
    assert none.json() == headers.json()
    assert future.json() == {
        "errorCode": "ATLAS-400-00-029",
        "errorMessage": "fromTimestamp should be less than toTimestamp",
    }
    assert (text.status_code, text.json()["errorMessage"]) == (
        400,
        "Invalid value soon for query parameter tagUpdateStartTime",
    )

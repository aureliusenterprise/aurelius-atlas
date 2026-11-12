"""The admin audits on the dev store: a purge audited and detailed, found by a search (ADA-02, ADA-04, ADA-05)."""

import uuid

import httpx2 as httpx
import pytest


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_atlas_audits",
    "aurelius_atlas_server.routes.admin.get_audit_details",
    rules=["ADA-02", "ADA-04", "ADA-05"],
)
async def test__a_purge_is_found_among_the_admin_audits_with_its_entity(client: httpx.AsyncClient) -> None:
    """The purge's entry, found by its parameters, details the purged entity."""
    run = uuid.uuid4().hex
    name = f"e2e_ada_{run}"
    types = {"entityDefs": [{"name": name, "superTypes": ["DataSet"]}]}
    assert (await client.post("/api/atlas/v2/types/typedefs", json=types)).status_code == 200
    body = {"entity": {"typeName": name, "attributes": {"qualifiedName": f"q_{run}", "name": run}}}
    guid = (await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"]
    assert (await client.delete(f"/api/atlas/v2/entity/guid/{guid}")).status_code == 200
    assert (await client.put("/api/atlas/admin/purge", json=[guid])).status_code == 200

    criterion = {"attributeName": "params", "operator": "eq", "attributeValue": f"[{guid}]"}
    search = {"auditFilters": {"condition": "AND", "criterion": [criterion]}, "limit": 5}
    found = (await client.post("/api/atlas/admin/audits", json=search)).json()
    [entry] = found
    details = (await client.get(f"/api/atlas/admin/audit/{entry['guid']}/details")).json()

    assert (entry["operation"], entry["result"], entry["resultCount"]) == ("PURGE", guid, 1)
    assert [header["guid"] for header in details] == [guid]

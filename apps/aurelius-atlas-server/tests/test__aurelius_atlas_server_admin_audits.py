"""``POST /api/atlas/admin/audits`` and ``GET /api/atlas/admin/audit/{guid}/details`` (ADA-02 to ADA-05), as Apache
Atlas 2.4.0's ``AdminResource`` writes and reads its admin audits.
"""  # noqa: D205 - one sentence

from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from base_models import base_models
from fake_issuer import FakeIssuer

ADMIN = "/api/atlas/admin"
TYPES = {"entityDefs": [{"name": "t_ada", "superTypes": ["DataSet"]}]}


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model, which holds ``__AtlasAuditEntry`` (ADA-01)."""
    return base_models(tmp_path)


async def audits(client: httpx.AsyncClient, operation: str) -> list[dict[str, Any]]:
    """The admin audits of the operation, newest first."""
    body = {
        "auditFilters": {
            "condition": "AND",
            "criterion": [{"attributeName": "operation", "operator": "eq", "attributeValue": operation}],
        },
        "sortBy": "startTime",
        "sortOrder": "DESCENDING",
        "limit": 10,
    }
    found = await client.post(f"{ADMIN}/audits", json=body)
    assert found.status_code == 200
    return found.json()


async def entity(client: httpx.AsyncClient, name: str) -> str:
    """The GUID of a new ``t_ada`` of the name."""
    body = {"entity": {"typeName": "t_ada", "attributes": {"qualifiedName": name, "name": name}}}
    return str((await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"])


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_atlas_audits",
    "aurelius_atlas_server.request_context.RequestContextMiddleware.dispatch",
    "aurelius_atlas_server.app._audit_server_status",
    rules=["ADA-02", "ADA-03", "ADA-04"],
)
async def test__the_start_and_type_changes_are_audited(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """The server's start and activation; a type created by the request's user and client; ``ADMIN_AUDITS`` asked."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200

    [start] = await audits(client, "SERVER_START")
    [active] = await audits(client, "SERVER_STATE_ACTIVE")
    created = await audits(client, "TYPE_DEF_CREATE")
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}
    refused = await client.post(f"{ADMIN}/audits", json={}, headers=reader)
    missing = await client.post(f"{ADMIN}/audits")
    wrong = await client.post(f"{ADMIN}/audits", json={"sortBy": "nope"})
    invalid = await client.post(f"{ADMIN}/audits", json=["x"])

    assert start["startTime"] <= start["endTime"] == active["startTime"]
    assert (created[0]["userName"], created[0]["params"], created[0]["resultCount"]) == ("admin", "ENTITY", 1)
    assert created[0]["clientId"] == "127.0.0.1"
    assert created[-1]["resultCount"] > 1  # the base model, loaded at the start
    assert (refused.status_code, refused.json()["errorMessage"]) == (
        403,
        "reader is not authorized to perform Admin Audits",
    )
    assert (missing.status_code, missing.json()["errorMessage"]) == (
        400,
        "invalid parameters: Audit Search Parameters not specified",
    )
    assert (wrong.status_code, wrong.json()["errorCode"]) == (400, "ATLAS-400-00-023")
    assert invalid.status_code == 400


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.purge_by_ids",
    "aurelius_atlas_server.routes.admin.get_audit_details",
    rules=["ADA-02", "ADA-05"],
)
async def test__a_purge_is_audited_with_the_entities_it_purged(client: httpx.AsyncClient) -> None:
    """The purge's GUIDs and count; its details the purged entities' headers, a page of them."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    guids = [await entity(client, name) for name in ("a", "b")]
    for guid in guids:
        assert (await client.delete(f"/api/atlas/v2/entity/guid/{guid}")).status_code == 200
    assert (await client.put(f"{ADMIN}/purge", json=guids)).status_code == 200
    assert (await client.put(f"{ADMIN}/purge", json=guids)).status_code == 200  # nothing purged: no audit

    [purge] = await audits(client, "PURGE")
    details = await client.get(f"{ADMIN}/audit/{purge['guid']}/details")
    page = await client.get(f"{ADMIN}/audit/{purge['guid']}/details", params={"limit": "1", "offset": "1"})
    [start] = await audits(client, "SERVER_START")
    none = await client.get(f"{ADMIN}/audit/{start['guid']}/details")

    assert (purge["params"], purge["resultCount"]) == (f"[{guids[0]}, {guids[1]}]", 2)
    assert sorted(purge["result"].split(",")) == sorted(guids)
    assert sorted(header["guid"] for header in details.json()) == sorted(guids)
    assert [header["guid"] for header in page.json()] == purge["result"].split(",")[1:]
    assert (none.status_code, none.json()) == (200, [])
    assert (await client.get(f"{ADMIN}/audit/missing/details")).status_code == 404


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.export",
    "aurelius_atlas_server.routes.admin.import_data",
    "aurelius_atlas_server.routes.admin._audit_items",
    "aurelius_atlas_server.routes.admin._audit_import",
    rules=["ADA-02"],
)
async def test__an_export_and_an_import_are_audited_by_the_items_they_name(client: httpx.AsyncClient) -> None:
    """An export with options: its items by type; without options: none; an import: its export's items (DV-131)."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    guid = await entity(client, "x")
    by_name = {"typeName": "t_ada", "uniqueAttributes": {"qualifiedName": "x"}}
    request = {"itemsToExport": [by_name, {"guid": guid}], "options": {"fetchType": "full"}}

    content = (await client.post(f"{ADMIN}/export", json=request)).content
    await client.post(f"{ADMIN}/export", json={"itemsToExport": [{"guid": guid}]})
    imported = await client.post(f"{ADMIN}/import", files={"data": ("e.zip", content)})

    [exported] = await audits(client, "EXPORT")
    [into] = await audits(client, "IMPORT")
    assert imported.status_code == 200
    assert exported["params"] == '{"fetchType":"full","operationStatus":"SUCCESS"}'
    assert (exported["result"], exported["resultCount"]) == ('{"t_ada":1}', 2)
    assert (into["params"], into["result"], into["resultCount"]) == ('{"operationStatus":"SUCCESS"}', '{"t_ada":1}', 2)

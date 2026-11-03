"""``GET /api/atlas/admin/server/{serverName}`` and ``GET /api/atlas/admin/expimp/audit`` (REP-01, REP-05), as
Apache Atlas 2.4.0's ``AdminResource#getCluster`` and ``#getExportImportAudit``.
"""  # noqa: D205 - one sentence

from pathlib import Path

import httpx2 as httpx
import pytest
from base_models import base_models
from fake_issuer import FakeIssuer

ADMIN = "/api/atlas/admin"
TYPES = {"entityDefs": [{"name": "t_rep", "superTypes": ["DataSet"]}]}


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: an export or import records its servers and audit entry (REP-02)."""
    return base_models(tmp_path)


async def exported(client: httpx.AsyncClient) -> str:
    """The GUID of a new ``t_rep``, exported to ``dc$cl2``."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    body = {"entity": {"typeName": "t_rep", "attributes": {"qualifiedName": "r", "name": "r"}}}
    guid = str((await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"])
    request = {"itemsToExport": [{"guid": guid}], "options": {"replicatedTo": "dc$cl2"}}
    assert (await client.post(f"{ADMIN}/export", json=request)).status_code == 200
    return guid


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_cluster",
    "aurelius_atlas_server.routes.admin.export",
    "aurelius_atlas_server.routes.admin._audits",
    rules=["REP-01", "REP-04"],
)
async def test__a_server_an_export_named_answers_with_its_replication(client: httpx.AsyncClient) -> None:
    """The target by its full name, the exported entity in its details; a server not there is 404."""
    guid = await exported(client)

    found = await client.get(f"{ADMIN}/server/dc$cl2")
    this = await client.get(f"{ADMIN}/server/default")
    missing = await client.get(f"{ADMIN}/server/none")
    entity = (await client.get(f"/api/atlas/v2/entity/guid/{guid}")).json()["entity"]

    assert found.status_code == 200
    server = found.json()
    assert (server["name"], server["fullName"], server["displayName"]) == ("cl2", "dc$cl2", "cl2")
    assert guid in server["additionalInfo"]["REPL_DETAILS"]
    assert this.json()["name"] == "default"
    assert (missing.status_code, missing.json()["errorCode"]) == (404, "ATLAS-404-00-009")
    assert entity["attributes"]["replicatedTo"] == [{"typeName": "AtlasServer", "guid": server["guid"]}]


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_export_import_audit", rules=["REP-05"])
async def test__the_audit_trail_answers_the_entries_asked_for(client: httpx.AsyncClient) -> None:
    """The export's entry by server and operation; none for another user."""
    await exported(client)

    found = await client.get(f"{ADMIN}/expimp/audit", params={"serverName": "cl2", "operation": "EXPORT"})
    other = await client.get(f"{ADMIN}/expimp/audit", params={"userName": "nobody", "limit": "5"})

    assert found.status_code == 200
    [entry] = found.json()
    assert (entry["userName"], entry["sourceServerName"], entry["targetServerName"]) == ("admin", "default", "cl2")
    assert entry["operation"] == "EXPORT"
    assert entry["startTime"] <= entry["endTime"]
    assert other.json() == []


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_cluster",
    "aurelius_atlas_server.routes.admin.get_export_import_audit",
    rules=["REP-01", "REP-05"],
)
async def test__the_servers_and_entries_are_read_as_entities(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """No admin privilege is asked; a user who may not read entities is refused the server, sees no entry (DV-130)."""
    await exported(client)
    admin_only = {"Authorization": f"Bearer {issuer.token('admin2', atlas_roles=('atlas-admin',))}"}
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}

    refused = await client.get(f"{ADMIN}/server/dc$cl2", headers=admin_only)
    hidden = await client.get(f"{ADMIN}/expimp/audit", headers=admin_only)
    read = await client.get(f"{ADMIN}/server/dc$cl2", headers=reader)

    assert refused.status_code == 403
    assert (hidden.status_code, hidden.json()) == (200, [])
    assert read.json()["name"] == "cl2"

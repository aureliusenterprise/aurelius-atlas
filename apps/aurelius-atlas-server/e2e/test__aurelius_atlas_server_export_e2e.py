"""An export from the container on the dev store: a ZIP of what an entity reaches (EXP-01, EXP-04, EXP-06).

The scenarios do not compare a binary body; this reads the ZIP the server answers over TLS.
"""

import io
import json
import uuid
import zipfile

import httpx2 as httpx
import pytest


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.export",
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.of_types",
    rules=["EXP-01", "EXP-04", "EXP-06"],
)
async def test__an_export_answers_the_zip_of_what_an_entity_reaches(client: httpx.AsyncClient) -> None:
    """A table and its database, related both ways, exported from the table: both, the order, types and result."""
    run = uuid.uuid4().hex
    db, table = f"e2e_export_db_{run}", f"e2e_export_table_{run}"
    unique = {"name": "qualifiedName", "typeName": "string", "isUnique": True, "isIndexable": True}
    types = {
        "entityDefs": [{"name": db, "attributeDefs": [unique]}, {"name": table, "attributeDefs": [unique]}],
        "relationshipDefs": [
            {
                "name": f"e2e_export_rel_{run}",
                "relationshipCategory": "ASSOCIATION",
                "endDef1": {"type": table, "name": "db", "cardinality": "SINGLE"},
                "endDef2": {"type": db, "name": "tables", "cardinality": "SET"},
            }
        ],
    }
    assert (await client.post("/api/atlas/v2/types/typedefs", json=types)).status_code == 200
    entities = {
        "entities": [
            {"typeName": db, "guid": "-1", "attributes": {"qualifiedName": f"d_{run}"}},
            {
                "typeName": table,
                "guid": "-2",
                "attributes": {"qualifiedName": f"t_{run}"},
                "relationshipAttributes": {"db": {"typeName": db, "guid": "-1"}},
            },
        ]
    }
    created = (await client.post("/api/atlas/v2/entity/bulk", json=entities)).json()["guidAssignments"]

    found = await client.post(
        "/api/atlas/admin/export",
        json={"itemsToExport": [{"typeName": table, "uniqueAttributes": {"qualifiedName": f"t_{run}"}}]},
    )

    assert found.status_code == 200
    with zipfile.ZipFile(io.BytesIO(found.content)) as archive:
        order = json.loads(archive.read("atlas-export-order.json"))
        types_def = json.loads(archive.read("atlas-typesdef.json"))
        info = json.loads(archive.read("atlas-export-info.json"))
    assert order == [created["-2"], created["-1"]]
    assert {typedef["name"] for typedef in types_def["entityDefs"]} == {table, db}
    assert info["operationStatus"] == "SUCCESS"


@pytest.mark.covers("aurelius_atlas_server.routes.admin.import_data", rules=["IMS-01", "IMS-04"])
async def test__an_export_imports_back_into_the_catalogue(client: httpx.AsyncClient) -> None:
    """The ZIP of an entity, imported again: its entity known by its GUID, the import a success."""
    run = uuid.uuid4().hex
    name = f"e2e_import_{run}"
    types = {
        "entityDefs": [
            {"name": name, "attributeDefs": [{"name": "qualifiedName", "typeName": "string", "isUnique": True}]}
        ]
    }
    assert (await client.post("/api/atlas/v2/types/typedefs", json=types)).status_code == 200
    body = {"entity": {"typeName": name, "attributes": {"qualifiedName": f"q_{run}"}}}
    guid = (await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"]
    content = (await client.post("/api/atlas/admin/export", json={"itemsToExport": [{"guid": guid}]})).content

    found = await client.post("/api/atlas/admin/import", files={"data": ("export.zip", content)})

    assert found.status_code == 200
    assert found.json()["operationStatus"] == "SUCCESS"
    assert found.json()["exportResult"]["request"]["itemsToExport"] == [{"guid": guid}]


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_cluster",
    "aurelius_atlas_server.routes.admin.get_export_import_audit",
    rules=["REP-01", "REP-02", "REP-04", "REP-05"],
)
async def test__a_replicating_export_is_audited_and_marks_its_entity(client: httpx.AsyncClient) -> None:
    """The target server saved, the entity marked ``replicatedTo`` it, the export found in the audit trail."""
    run = uuid.uuid4().hex
    name, server = f"e2e_repl_{run}", f"e2e_server_{run}"
    assert (
        await client.post(
            "/api/atlas/v2/types/typedefs", json={"entityDefs": [{"name": name, "superTypes": ["DataSet"]}]}
        )
    ).status_code == 200
    body = {"entity": {"typeName": name, "attributes": {"qualifiedName": f"q_{run}", "name": run}}}
    guid = (await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"]
    request = {"itemsToExport": [{"guid": guid}], "options": {"replicatedTo": f"dc${server}"}}
    assert (await client.post("/api/atlas/admin/export", json=request)).status_code == 200

    target = (await client.get(f"/api/atlas/admin/server/dc${server}")).json()
    entity = (await client.get(f"/api/atlas/v2/entity/guid/{guid}")).json()["entity"]
    audits = (await client.get("/api/atlas/admin/expimp/audit", params={"serverName": server})).json()

    assert target["name"] == server
    assert guid in target["additionalInfo"]["REPL_DETAILS"]
    assert entity["attributes"]["replicatedTo"] == [{"typeName": "AtlasServer", "guid": target["guid"]}]
    assert [(entry["operation"], entry["targetServerName"]) for entry in audits] == [("EXPORT", server)]

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

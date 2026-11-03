"""The export/import pair through the client library, against the container (CL-11, CLW-03, CLW-04).

The scenarios do not compare a binary body; this reads the ZIP the server answers over TLS.
The typed twin of the raw scenario calls: the bodies cross as ``aurelius-atlas-model``
contracts (CL-10), so 8.11's ``admin.export`` and ``admin.import_data`` are proven against
the real routes, the way the search e2e proves CL-13.
"""

import io
import json
import uuid
import zipfile

import httpx2 as httpx
import pytest
from aurelius_atlas_model.impexp import AtlasExportRequest, OperationStatus
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityWithExtInfo,
    AtlasObjectId,
    EntityOperation,
)
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypesDef,
    Cardinality,
    RelationshipCategory,
)
from aurelius_atlas_server_client import AtlasClient

QUALIFIED_NAME = AtlasAttributeDef(name="qualifiedName", type_name="string", is_unique=True, is_indexable=True)
"""The unique, indexable attribute every entity type below defines."""


def _qualified(name: str) -> AtlasEntityDef:
    """An entity type whose only attribute is the unique, indexable qualified name."""
    return AtlasEntityDef(name=name, attribute_defs=[QUALIFIED_NAME])


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.export",
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.of_types",
    "aurelius_atlas_server_client.client.TypesApi.create_typedefs",
    "aurelius_atlas_server_client.client.EntityApi.create_or_update_bulk",
    "aurelius_atlas_server_client.client.AdminApi.export",
    rules=["EXP-01", "EXP-04", "EXP-06", "CLW-03"],
)
async def test__an_export_answers_the_zip_of_what_an_entity_reaches(api: AtlasClient) -> None:
    """A table and its database, related both ways, exported from the table: both, the order, types and result."""
    run = uuid.uuid4().hex
    db, table = f"e2e_export_db_{run}", f"e2e_export_table_{run}"
    types = AtlasTypesDef(
        entity_defs=[_qualified(db), _qualified(table)],
        relationship_defs=[
            AtlasRelationshipDef(
                name=f"e2e_export_rel_{run}",
                relationship_category=RelationshipCategory.ASSOCIATION,
                end_def1=AtlasRelationshipEndDef(type=table, name="db", cardinality=Cardinality.SINGLE),
                end_def2=AtlasRelationshipEndDef(type=db, name="tables", cardinality=Cardinality.SET),
            )
        ],
    )
    await api.types.create_typedefs(types)
    entities = AtlasEntitiesWithExtInfo(
        entities=[
            AtlasEntity(guid="-1", type_name=db, attributes={"qualifiedName": f"d_{run}"}),
            AtlasEntity(
                guid="-2",
                type_name=table,
                attributes={"qualifiedName": f"t_{run}"},
                relationship_attributes={"db": {"typeName": db, "guid": "-1"}},
            ),
        ]
    )
    created = (await api.entity.create_or_update_bulk(entities)).guid_assignments
    assert created is not None

    content, _ = await api.admin.export(
        AtlasExportRequest(
            items_to_export=[AtlasObjectId(type_name=table, unique_attributes={"qualifiedName": f"t_{run}"})]
        )
    )

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        order = json.loads(archive.read("atlas-export-order.json"))
        types_def = json.loads(archive.read("atlas-typesdef.json"))
        info = json.loads(archive.read("atlas-export-info.json"))
    assert order == [created["-2"], created["-1"]]
    assert {typedef["name"] for typedef in types_def["entityDefs"]} == {table, db}
    assert info["operationStatus"] == "SUCCESS"


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.import_data",
    "aurelius_atlas_server_client.client.TypesApi.create_typedefs",
    "aurelius_atlas_server_client.client.EntityApi.create_or_update",
    "aurelius_atlas_server_client.client.AdminApi.export",
    "aurelius_atlas_server_client.client.AdminApi.import_data",
    rules=["IMS-01", "IMS-04", "CLE-01", "CLW-03", "CLW-04"],
)
async def test__an_export_imports_back_into_the_catalogue(api: AtlasClient) -> None:
    """The ZIP of an entity, imported again: its entity known by its GUID, the import a success."""
    run = uuid.uuid4().hex
    name = f"e2e_import_{run}"
    await api.types.create_typedefs(AtlasTypesDef(entity_defs=[_qualified(name)]))
    body = AtlasEntityWithExtInfo(entity=AtlasEntity(type_name=name, attributes={"qualifiedName": f"q_{run}"}))
    created = (await api.entity.create_or_update(body)).get_first_entity_by_operation(EntityOperation.CREATE)
    assert created is not None
    assert created.guid is not None
    guid = created.guid
    content, _ = await api.admin.export(AtlasExportRequest(items_to_export=[AtlasObjectId(guid=guid)]))

    found = await api.admin.import_data(content)

    assert found.operation_status is OperationStatus.SUCCESS
    assert found.export_result is not None
    assert found.export_result.request is not None
    assert found.export_result.request.items_to_export == [AtlasObjectId(guid=guid)]


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

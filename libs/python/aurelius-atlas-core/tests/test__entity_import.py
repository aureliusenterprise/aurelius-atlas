"""An import's write of entities (IMP-01 to IMP-08) on the in-memory documents.

Read from Apache Atlas 2.4.0's ``AtlasEntityStoreV2#createOrUpdateForImport`` and the branches of ``preCreateOrUpdate``,
``IDBasedEntityResolver``, ``EntityGraphMapper`` (``createVertexWithGuid``, ``updateSystemAttributes``,
``importActivateEntity``, the relationship GUIDs) and ``EntityAuditListenerV2`` that ``isImportInProgress`` takes.
"""

import itertools
import json
from typing import Any

import pytest
from aurelius_atlas_core.authorization import Granted
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter, with_system_attributes
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository, MemoryEntityDocuments
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntityWithExtInfo, EntityOperation
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

W = "aurelius_atlas_core.entity_writer"
A = EntityAuditActionV2
DB, TABLE = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
MISSING = "33333333-3333-3333-3333-333333333333"
RELATIONSHIP = "44444444-4444-4444-4444-444444444444"
ON = '["imp_table"]'
TYPES = {
    "classificationDefs": [{"name": "PII"}, {"name": "Gold"}],
    "entityDefs": [{"name": "imp_db", "superTypes": ["Asset"]}, {"name": "imp_table", "superTypes": ["DataSet"]}],
    "relationshipDefs": [
        {
            "name": "imp_table_db",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "imp_table", "name": "db", "cardinality": "SINGLE"},
            "endDef2": {"type": "imp_db", "name": "tables", "cardinality": "SET"},
        }
    ],
    "businessMetadataDefs": [
        {
            "name": "bm",
            "attributeDefs": [
                {"name": "rank", "typeName": "int", "isOptional": True, "options": {"applicableEntityTypes": ON}}
            ],
        }
    ],
}


@pytest.fixture
def audits() -> InMemoryEntityAuditRepository:
    """The events recorded."""
    return InMemoryEntityAuditRepository()


@pytest.fixture
def store() -> EntityStore:
    """A store of the base model, a database and table type, two classifications and business metadata."""
    registry = TypeRegistry()
    with registry.update() as transient:
        model = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
        transient.add_types(AtlasTypesDef.model_validate(model))
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    ticks = itertools.count(1_700_000_000_000)
    return EntityStore(registry, MemoryEntityDocuments(), clock=lambda: next(ticks) / 1000)


def importer(store: EntityStore, audits: InMemoryEntityAuditRepository) -> EntityWriter:
    """A writer as user ``admin``, refused every privilege, its changes audited."""
    notifier = EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])
    return EntityWriter(store, user="admin", notifier=notifier, authorizer=Granted("admin", frozenset()))


def table(**more: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The exported table: its GUID, times, users, version, labels and a reference to the database."""
    return {
        "typeName": "imp_table",
        "guid": TABLE,
        "status": "ACTIVE",
        "version": 3,
        "createTime": 1000,
        "updateTime": 2000,
        "createdBy": "alice",
        "updatedBy": "bob",
        "labels": ["l1"],
        "customAttributes": {"k": "v"},
        "attributes": {"qualifiedName": "t", "name": "t"},
        "relationshipAttributes": {
            "db": {
                "guid": DB,
                "typeName": "imp_db",
                "relationshipGuid": RELATIONSHIP,
                "relationshipType": "imp_table_db",
            },
        },
        **more,
    }


def database(**more: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The exported database."""
    return {"typeName": "imp_db", "guid": DB, "attributes": {"qualifiedName": "d", "name": "d"}, **more}


async def run(writer: EntityWriter, entity: dict[str, Any]) -> dict[str, Any]:
    """The answer to importing the entity, as JSON."""
    return (
        await writer.create_or_update_for_import(AtlasEntityWithExtInfo.model_validate({"entity": entity}))
    ).to_json()


async def stored(store: EntityStore, guid: str) -> dict[str, Any]:
    """The entity as a read answers it."""
    found = (await EntityRetriever(store).entity_with_ext_info(guid)).entity
    assert found is not None
    return found.to_json()


def actions(audits: InMemoryEntityAuditRepository) -> list[tuple[str, EntityAuditActionV2 | None]]:
    """The audit events' entities and actions, in order."""
    return [(event.entity_id or "", event.action) for event in audits.events]


@pytest.mark.covers(
    f"{W}.EntityWriter.create_or_update_for_import",
    f"{W}.with_system_attributes",
    "aurelius_atlas_core.entity_discovery.EntityDiscovery.discover",
    rules=["IMP-01", "IMP-02", "IMP-03", "IMP-05", "IMP-07", "IMP-08"],
)
async def test__an_imported_entity_keeps_its_guid_and_system_attributes(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Created with its GUID, version, creator and labels, unchecked; a reference to an entity not there left out."""
    writer = importer(store, audits)

    created = await run(writer, table())
    read = await stored(store, TABLE)

    assert [header["guid"] for header in created["mutatedEntities"]["CREATE"]] == [TABLE]
    assert (read["version"], read["createTime"], read["createdBy"]) == (3, 1000, "alice")
    assert read["updatedBy"] == "admin"  # mapAttributes sets it, as the entity gives attributes
    assert (read["labels"], read["customAttributes"]) == (["l1"], {"k": "v"})
    assert read["relationshipAttributes"]["db"] is None
    assert actions(audits) == [(TABLE, A.LABEL_ADD), (TABLE, A.ENTITY_IMPORT_CREATE)]
    bare = with_system_attributes(
        (await store.get(TABLE)).entity,  # type: ignore[union-attr]
        AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [{"typeName": "imp_db", "updateTime": 5, "updatedBy": "c"}]}
        ).entities[0],  # type: ignore[index]
    )
    assert (bare.update_time, bare.updated_by) == (5, "c")


@pytest.mark.covers("aurelius_atlas_core.relationship_mapper.RelationshipMapper.map", rules=["IMP-05"])
async def test__an_imported_relationship_keeps_its_guid(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Once its other end is there, the reference makes the relationship of the GUID it names."""
    writer = importer(store, audits)
    await run(writer, database())
    await run(writer, table())

    read = await stored(store, TABLE)

    assert read["relationshipAttributes"]["db"]["relationshipGuid"] == RELATIONSHIP
    assert read["relationshipAttributes"]["db"]["guid"] == DB


@pytest.mark.covers(
    f"{W}.EntityWriter.create_or_update_for_import",
    "aurelius_atlas_core.entity_comparator.EntityComparator.has_difference",
    rules=["IMP-06", "IMP-08"],
)
async def test__an_import_replaces_classifications_and_business_attributes(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """The stored ones replaced, audited as an import's; an entity alike in everything is left alone."""
    writer = importer(store, audits)
    await run(writer, database())  # so the table's reference reads as given
    await run(writer, table(classifications=[{"typeName": "PII"}], businessAttributes={"bm": {"rank": 1}}))
    audits.events.clear()

    changed = await run(
        writer, table(classifications=[{"typeName": "Gold"}], businessAttributes={"bm": {"rank": 2}}, labels=["l2"])
    )
    read = await stored(store, TABLE)

    assert [c["typeName"] for c in read["classifications"]] == ["Gold"]
    assert read["classifications"][0]["propagate"] is False
    assert read["businessAttributes"] == {"bm": {"rank": 2}}
    assert read["labels"] == ["l2"]
    assert [header["guid"] for header in changed["mutatedEntities"]["UPDATE"]] == [TABLE]
    found = [action for _, action in actions(audits)]
    assert A.ENTITY_IMPORT_UPDATE in found
    assert {
        A.LABEL_DELETE,
        A.LABEL_ADD,
        A.BUSINESS_ATTRIBUTE_UPDATE,
        A.CLASSIFICATION_DELETE,
        A.CLASSIFICATION_ADD,
    } <= set(found)
    audits.events.clear()
    same = await run(
        writer, table(classifications=read["classifications"], businessAttributes={"bm": {"rank": 2}}, labels=["l2"])
    )
    assert "UPDATE" not in (same.get("mutatedEntities") or {})


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update_for_import", rules=["IMP-04", "IMP-08"])
async def test__an_import_deletes_and_reactivates_by_status(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """``DELETED`` deletes an active entity, ``ACTIVE`` revives a deleted one with its relationships."""
    writer = importer(store, audits)
    await run(writer, database())
    await run(writer, table())

    removed = await run(writer, table(status="DELETED"))
    assert [header["guid"] for header in removed["mutatedEntities"]["DELETE"]] == [TABLE]
    assert (await stored(store, TABLE))["status"] == "DELETED"
    assert (TABLE, A.ENTITY_IMPORT_DELETE) in actions(audits)

    revived = await run(writer, table())
    read = await stored(store, TABLE)
    assert [header["guid"] for header in revived["mutatedEntities"]["CREATE"]] == [TABLE]
    assert read["status"] == "ACTIVE"
    assert read["relationshipAttributes"]["db"]["relationshipStatus"] == "ACTIVE"
    assert EntityOperation.CREATE.value in revived["mutatedEntities"]

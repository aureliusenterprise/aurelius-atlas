"""Replication bookkeeping and the export/import audit trail (REP-01 to REP-05), on the in-memory documents.

Read from Apache Atlas 2.4.0's ``AuditsWriter``, ``AtlasServerService``, ``ExportImportAuditService`` and their DTOs,
and its ``ReplicationEntityAttributeTest``, ``ExportImportAuditServiceTest`` and ``AtlasServerServiceTest``: a table
exported to ``cl2`` and imported there from ``cl1``.
"""

import json
from typing import Any

import pytest
from aurelius_atlas_core.atlas_server_service import AtlasServerService
from aurelius_atlas_core.audits_writer import AuditsWriter, hive_db_qualified_name, repl_key_guid, server_name_of
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.export_import_audit_service import ExportImportAuditService
from aurelius_atlas_core.export_service import ExportService
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, ModelLoader
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.impexp import (
    AtlasExportRequest,
    AtlasImportRequest,
    AtlasServer,
    skip_update_replication_attr,
)
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

C = "aurelius_atlas_core"
TYPES = {"entityDefs": [{"name": "rep_table", "superTypes": ["DataSet"]}]}


async def catalogue() -> tuple[EntityStore, TypedefStore]:
    """An entity store of the built-in models (Hive's among them), their patches, and a table type."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    await ModelLoader(types).load(BUILTIN_MODELS_DIR)
    await types.create_types_def(AtlasTypesDef.model_validate(TYPES))
    return EntityStore(types.registry, MemoryEntityDocuments()), types


async def table(store: EntityStore) -> str:
    """The GUID of a new table ``t``."""
    body = {"entities": [{"typeName": "rep_table", "guid": "-1", "attributes": {"qualifiedName": "t", "name": "t"}}]}
    created = await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate(body))
    return (created.guid_assignments or {})["-1"]


async def exported(store: EntityStore, guid: str, **options: object) -> bytes:
    """The ZIP of the table's export from ``cl1``, audited."""
    sink = ZipSink()
    request = AtlasExportRequest.model_validate({"itemsToExport": [{"guid": guid}], "options": options})
    audits = AuditsWriter(store, cluster_name="cl1", user="exporter")
    await ExportService(store, cluster_name="cl1", audits=audits).run(sink, request, "exporter", "h", "ip")
    return sink.close()


async def replicated(store: EntityStore, guid: str, name: str) -> Any:  # noqa: ANN401 - attribute values
    """The table's ``replicatedTo`` or ``replicatedFrom`` as a read answers it."""
    found = (await EntityRetriever(store).entity_with_ext_info(guid)).entity
    assert found is not None
    return found.to_json()["attributes"].get(name)


@pytest.mark.covers(
    f"{C}.audits_writer.AuditsWriter.write_export",
    f"{C}.audits_writer.AuditsWriter.write_import",
    f"{C}.atlas_server_service.AtlasServerService.get",
    f"{C}.atlas_server_service.AtlasServerService.get_create_atlas_server",
    f"{C}.atlas_server_service.AtlasServerService.save",
    f"{C}.atlas_server_service.AtlasServerService.update_entities_with_server",
    f"{C}.atlas_server_service.AtlasServerDTO.from_entity",
    f"{C}.atlas_server_service.AtlasServerDTO.to_entities",
    f"{C}.atlas_server_service.AtlasServerDTO.unique_attributes",
    "aurelius_atlas_model.impexp.AtlasServer.set_additional_info_repl",
    "aurelius_atlas_model.impexp.replicated",
    rules=["REP-01", "REP-03", "REP-04"],
)
async def test__a_replicating_export_and_import_mark_the_servers_and_entities() -> None:
    """Both servers saved; the target's details name the table and export time; the table names its servers."""
    store, types = await catalogue()
    guid = await table(store)

    content = await exported(store, guid, replicatedTo="dc1$cl2")
    servers = AtlasServerService(store)
    target = await servers.get(AtlasServer(full_name="dc1$cl2"))
    assert (await servers.get(AtlasServer(full_name="cl1"))).name == "cl1"
    assert (target.name, target.display_name) == ("cl2", "cl2")
    details = json.loads((target.additional_info or {})["REPL_DETAILS"])
    assert list(details) == [guid]
    assert await replicated(store, guid, "replicatedTo") == [{"typeName": "AtlasServer", "guid": target.guid}]

    await exported(store, guid, replicatedTo="dc1$cl2")
    assert len(await replicated(store, guid, "replicatedTo")) == 1  # added once

    other, other_types = await catalogue()
    request = AtlasImportRequest.model_validate({"options": {"replicatedFrom": "cl1"}})
    audits = AuditsWriter(other, cluster_name="cl2", user="importer")
    await ImportService(other, other_types, EntityWriter(other), audits=audits).run(content, request, "i", "h", "ip")
    source = await AtlasServerService(other).get(AtlasServer(full_name="cl1"))
    assert await replicated(other, guid, "replicatedFrom") == [{"typeName": "AtlasServer", "guid": source.guid}]
    with pytest.raises(AtlasError):
        await servers.get(AtlasServer(full_name="unknown"))
    assert types.registry.entity_type("AtlasServer") is not None


@pytest.mark.covers(
    f"{C}.export_import_audit_service.ExportImportAuditService.add",
    f"{C}.export_import_audit_service.ExportImportAuditService.get",
    f"{C}.export_import_audit_service.ExportImportAuditEntryDTO.from_entity",
    f"{C}.export_import_audit_service.ExportImportAuditEntryDTO.to_entities",
    f"{C}.export_import_audit_service.ExportImportAuditEntryDTO.unique_attributes",
    f"{C}.export_import_audit_service.entry_of",
    "aurelius_atlas_core.export_service.ExportService.run",
    "aurelius_atlas_core.import_service.ImportService.run",
    rules=["REP-02", "REP-05"],
)
async def test__each_export_and_import_with_entities_is_an_audit_entry() -> None:
    """An entry per operation that had entities, found by user, operation and server; a migration is not audited."""
    store, types = await catalogue()
    guid = await table(store)

    content = await exported(store, guid)
    await exported(store, "missing")  # no entities: no entry
    audits = AuditsWriter(store, cluster_name="cl1", user="importer")
    importer = ImportService(store, types, EntityWriter(store), audits=audits)
    await importer.run(content, AtlasImportRequest.model_validate({"options": {"replicatedFrom": "cl0"}}), "i", "h", "")
    await importer.run(content, AtlasImportRequest.model_validate({"options": {"migration": "true"}}), "i", "h", "")
    service = ExportImportAuditService(store)

    every = await service.get(None, None, None, None, None, 0, 0)
    exports = await service.get("exporter", "EXPORT", "cl1", None, None, 10, 0)
    from_cl0 = await service.get(None, None, "cl0", None, None, 10, 0)

    assert sorted(entry.operation or "" for entry in every) == ["EXPORT", "IMPORT"]
    assert [(e.user_name, e.source_server_name, e.target_server_name) for e in exports] == [("exporter", "cl1", None)]
    summary = json.loads(exports[0].result_summary or "{}")
    assert "rep_table" in [d["name"] for d in summary["data"]["typesDef"]["entityDefs"]]  # the result with its data
    assert exports[0].start_time > 0
    assert [(e.operation, e.source_server_name, e.target_server_name) for e in from_cl0] == [("IMPORT", "cl0", "cl1")]
    assert await service.get(None, "IMPORT", "cl9", None, None, 10, 0) == []


@pytest.mark.covers(
    f"{C}.audits_writer.server_name_of",
    "aurelius_atlas_model.impexp.skip_update_replication_attr",
    rules=["REP-03", "REP-04"],
)
def test__a_server_name_is_the_part_after_its_data_center() -> None:
    """``getServerNameFromFullName``: ``dc$server`` is ``server``; a name without ``$`` is itself.

    ``skipUpdateReplicationAttr`` is true as a boolean or as ``true`` in any case.
    """
    assert skip_update_replication_attr({"skipUpdateReplicationAttr": True})
    assert skip_update_replication_attr({"skipUpdateReplicationAttr": "TRUE"})
    assert not skip_update_replication_attr({"skipUpdateReplicationAttr": "no"})
    assert not skip_update_replication_attr({})
    assert server_name_of("dc1$cl2") == "cl2"
    assert server_name_of("cl2") == "cl2"
    assert server_name_of("$cl2") == "cl2"
    assert server_name_of("") == ""
    assert server_name_of("$") == ""


@pytest.mark.covers(
    f"{C}.export_import_audit_service.ExportImportAuditService.add",
    f"{C}.atlas_server_service.AtlasServerService.update_entities_with_server",
    rules=["REP-02", "REP-04"],
)
async def test__an_oversized_import_entry_loses_its_entity_list() -> None:
    """Above the audit's size an import's summary keeps all but ``processedEntities``; unknown entities are skipped."""
    store, _ = await catalogue()
    service = ExportImportAuditService(store)
    large = json.dumps({"operationStatus": "SUCCESS", "processedEntities": ["g" * 40] * 30_000})

    await service.add("u", "a", "b", "IMPORT", large, 1, 2, has_data=True)
    await service.add("u", "a", "b", "IMPORT", "{}", 1, 2, has_data=False)
    found = await service.get("u", "IMPORT", None, "1", "2", 10, 0)

    assert len(found) == 1
    summary = json.loads(found[0].result_summary or "{}")
    assert (summary["operationStatus"], summary["processedEntities"]) == ("SUCCESS", [])  # read back as a result
    servers = AtlasServerService(store)
    saved = await servers.get_create_atlas_server("s", "s")
    await servers.update_entities_with_server(saved, ["missing"], "replicatedTo")
    await servers.update_entities_with_server(AtlasServer(full_name="unsaved"), ["missing"], "replicatedTo")
    unsaved = await servers.save(AtlasServer(full_name=None))
    assert unsaved.guid == "-1"


@pytest.mark.covers(f"{C}.audits_writer.repl_key_guid", f"{C}.audits_writer.hive_db_qualified_name", rules=["REP-04"])
async def test__a_hive_table_replicates_under_its_database() -> None:
    """``ReplKeyGuidFinder``: a ``hive_table`` keys the details by its ``hive_db``; others by themselves."""
    store, _ = await catalogue()
    entities = [
        {
            "typeName": "hive_db",
            "guid": "-1",
            "attributes": {"qualifiedName": "sales@cl1", "name": "sales", "clusterName": "cl1"},
        },
        {"typeName": "hive_table", "guid": "-2", "attributes": {"qualifiedName": "sales.orders@cl1", "name": "o"}},
        {"typeName": "hive_table", "guid": "-3", "attributes": {"qualifiedName": "other.t@cl1", "name": "t"}},
    ]
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    guids = created.guid_assignments or {}

    assert await repl_key_guid(store, guids["-2"]) == guids["-1"]
    assert await repl_key_guid(store, guids["-3"]) == guids["-3"]  # no such database
    assert await repl_key_guid(store, guids["-1"]) == guids["-1"]
    assert await repl_key_guid(store, "missing") == "missing"
    assert hive_db_qualified_name("db.t.c@cl") == "db@cl"
    assert hive_db_qualified_name("db") == "db@"
    assert hive_db_qualified_name(None) == "null@null"

# 6.3a Export

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-303, DD-304, DV-120 to DV-122; relies on DD-057, DD-061, DD-300

Atlas exports a set of entities, everything they reach, and the types they use as a ZIP that another Atlas
imports. This first part of 6.3 serves the export. Import, which is also how an existing Java Atlas is
migrated, follows in 6.3b. Import transforms, the Hive-specific incremental export, replication options and
the export and import audits follow in 6.3c.

## Scope

| Endpoint                       | Needs          |
| ------------------------------ | -------------- |
| `POST /api/atlas/admin/export` | `ADMIN_EXPORT` |

In `aurelius-atlas-model`, `impexp` (`AtlasExportRequest`, `AtlasExportResult`) and
`FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK`. In `aurelius-atlas-core`, `export_service`,
`start_entity_fetch_by_export_request`, `entities_extractor`, `vertex_extractor`,
`relationship_attributes_extractor`, `export_type_processor` and `zip_sink`, and `EntityStore.of_types`. In
`aurelius-atlas-server`, the route in `routes/admin`, the `cluster_name` setting and the export and import lock.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EXP-01 | `POST admin/export` takes an `AtlasExportRequest`, `itemsToExport` and `options`; no body is an empty request (DV-120), any other body is `BAD_REQUEST` (DV-10). It needs `ADMIN_EXPORT`, `export`. Unless the options name `skipLineage` or `replicatedTo`, one export or import runs at a time: another is `FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK` (409, `ATLAS-500-00-006`). It answers the ZIP, `application/zip`, `attachment; filename=AtlasExportResult`; with `omitZipResponseForEmptyExport`, an export that added no entity answers 204 without a body                                                                                                                                                                                                                                                                                           |
| EXP-02 | `fetchType` is `full` (the default, and for any other text), `connected` or `incremental`, in any case. `skipLineage` is a boolean or `true` in any case. `matchType` is the option's text. `changeMarker` is the epoch milliseconds an incremental export starts from                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| EXP-03 | An item starts from its GUID; with `matchType` `forType`, from every entity of the types its `typeName` lists apart by commas; else from the entities of exactly its type, in any state, whose stored value of a named attribute equals the item's, or, with `startsWith`, `endsWith`, `contains` or `matches` (a Java regular expression over the whole text), matches it as text. An attribute the type does not have, or a null value, is left out. An unknown type, or no entity found, fails the item                                                                                                                                                                                                                                                                                                                                               |
| EXP-04 | From each starting entity the export reaches further. An item of a type with relationship attributes follows them: a related entity is lineage when its type names `Process` among its own super types, and a relationship goes outward when the entity's type is the relationship type's end 1. An item of any other type follows every relationship and reference of its entities, in any state, from end 1 or the referring entity outward; an entity is lineage when it is a `Process`. A full export follows every one; a connected one follows a starting entity both ways, any other the way it was reached, a lineage entity outward, and a relationship of a lineage entity only against its own direction. `skipLineage` leaves lineage entities out. Lineage entities are processed after the others reached, round by round (DD-303)         |
| EXP-05 | Each entity reached is added once, with the entities it owns, as `<guid>.json` (`AtlasEntityWithExtInfo`), its GUID appended to the export order. Before an entity, the glossary and the term of each term in its `meanings` are added alone. An incremental export adds an entity only when it was updated at or after its `changeMarker`, else each of its owned entities that was, alone; it reaches as a full one does                                                                                                                                                                                                                                                                                                                                                                                                                               |
| EXP-06 | Then come `atlas-export-order.json`, the GUIDs in the order added; `atlas-typesdef.json`, the types used: each entity's type, its attributes' types, its relationship types with their end types, the business metadata that applies to it and its super types, each classification's type with its attributes' types and super types, by kind (DV-121); and `atlas-export-info.json`, the result: the request, the user, the client's address, the server's host name, the time, `metrics` (`entity:<type>` for each entity and owned entity added, `entity:withExtInfo` for each entity added, `duration` in milliseconds), `operationStatus` (each item's `SUCCESS` or `FAIL`; all alike, that; else `PARTIAL_SUCCESS`; none, `FAIL`), `sourceClusterName` (the `cluster_name` setting, `default` unless set) and `changeMarker` (the export's start) |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `export`, `acquireExportImportLock`
- `repository/.../impexp/ExportService.java`: `run`, `processItems`, `processObjectId`, `processEntity`,
  `addGlossaryEntities`, `addEntity`, `processTypesDef`, `getOverallOperationStatus`, `ExportContext`
- `repository/.../impexp/StartEntityFetchByExportRequest.java`, `EntitiesExtractor.java`, `VertexExtractor.java`,
  `RelationshipAttributesExtractor.java`, `ExportTypeProcessor.java`, `ZipSink.java`, `ZipExportFileNames.java`
- `repository/.../util/AtlasGremlin3QueryProvider.java`: the export queries
- `intg/.../model/impexp/AtlasExportRequest.java`, `AtlasExportResult.java`

## Deviations

- **DV-120:** the export does not declare `Content-Encoding: gzip`; Atlas declares it on a ZIP it does not
  compress further. An export without a body is an empty request; Atlas fails on the null.
- **DV-121:** the type definitions, the metrics and the starting entities found by value come in the order
  first met; Atlas's sets and maps give hash order.
- **DV-122:** an item of type `hdfs_path` is not created when it does not exist (`HdfsPathEntityCreator`).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__export_service.py` — EXP-02 to EXP-06 on the in-memory
  documents: full, connected and skipped lineage, starting entities, the vertex strategy and incremental.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_export.py` — EXP-01: the ZIP, the check, the lock.
- `apps/aurelius-atlas-server/scenarios/admin/export.scenario.yaml` and
  `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_export_e2e.py` — on Elasticsearch.
- `uv run aurelius-atlas-trace check`.

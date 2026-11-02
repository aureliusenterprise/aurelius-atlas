# 6.3b2 Import and migration

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-306, DV-125, DV-126; relies on DD-304, the import mode of 6.3b1 (IMP-01 to IMP-08)

The import reads an export's ZIP, merges its type definitions into the catalogue, and writes its entities
one by one through the import mode of 6.3b1. Importing an export of a Java Apache Atlas 2.4 is how an
existing Atlas is migrated: its entities, relationships and classifications keep their GUIDs. Import
transforms and transformers, replication and the export and import audits follow in 6.3c; until then the
`transforms` and `transformers` options are not applied.

## Scope

| Endpoint                           | Needs          |
| ---------------------------------- | -------------- |
| `POST /api/atlas/admin/import`     | `ADMIN_IMPORT` |
| `POST /api/atlas/admin/importfile` | `ADMIN_IMPORT` |

In `aurelius-atlas-model`, `AtlasImportRequest`, `AtlasImportResult`, `IMPORT_ATTEMPTING_EMPTY_ZIP` and
`INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED`. In `aurelius-atlas-core`, `import_service`, `zip_source`,
`import_type_def_processor` and `regular_import`. In `aurelius-atlas-server`, the two routes in `routes/admin`
and the `import_folder` setting.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| IMS-01 | `POST admin/import` takes a form of the ZIP as `data` and the request's JSON as `request` (`{}` when absent; text that is no request is none). It needs `ADMIN_IMPORT`, `importData`. Unless the request names `replicatedFrom`, one export or import runs at a time (`FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK`). It answers the `AtlasImportResult`: the request, the user, the client's address, the server's host, the time, `metrics`, `processedEntities`, `operationStatus` (`SUCCESS`) and the export's result                                          |
| IMS-02 | The ZIP's entries are read by name. A ZIP of no entries, one whose export order is `[]`, or a file that is no ZIP is empty: the import answers an empty result (no request, `FAIL`). The entities are read in the export order; `startGuid` starts after the entity it names when the order holds it, else `startPosition` after the entity at that position; an entity the ZIP does not hold is passed over                                                                                                                                               |
| IMS-03 | Unless the `updateTypeDefinition` option is other than `true`, the export's type definitions are merged first: their GUIDs dropped, those the catalogue lacks created and counted by kind (`typedef:entitydef` and the like, each kind counted when any is created), and those it has given the attributes or enum elements they lack, each counted (`typedef:entitydef:update`). An attribute the catalogue has with another type fails the import (`INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED`); an attribute that is a legacy relationship end is not added |
| IMS-04 | Each entity is written with what it owns as an import (6.3b1). An export of no entity fails (`INVALID_PARAMETERS`, `no entities to create/update.`). Each entity written is counted once by type and operation (`entity:<type>:created`, `:updated`, `:deleted`) and listed in `processedEntities`; an entity that names one not written yet (`INVALID_OBJECT_ID`) is written again after the rest; any other failure fails the import. `duration` counts its milliseconds                                                                                 |
| IMS-05 | An entity with a GUID not stored, whose unique values another stored entity holds, is written as that entity: its GUID stands for the stored one for the rest of the import (DD-306, DV-126)                                                                                                                                                                                                                                                                                                                                                               |
| IMS-06 | `POST admin/importfile` takes the request as JSON and imports the ZIP its `fileName` option names; it needs `ADMIN_IMPORT`, `importFile`, and locks other exports and imports out only when the request names `replicatedFrom`, as Atlas does. A blank name is `INVALID_PARAMETERS`, `FILENAME parameter not found`; the file is read only from the server's `import_folder`, and a name outside it, or any name without one, is `<name>: file not found` (DV-125). An empty ZIP fails, as Atlas's check for it does not match                             |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `importData`, `importFile`
- `repository/.../impexp/ImportService.java`: `run` (stream and file), `processTypes`, `processEntities`,
  `setStartPosition`
- `repository/.../impexp/ZipSource.java`, `ImportTypeDefProcessor.java`, `TypeAttributeDifference.java`
- `repository/.../store/graph/v2/bulkimport/RegularImport.java`, `BulkImporterImpl.java` (`updateImportMetrics`)
- `repository/.../store/bootstrap/AtlasTypeDefStoreInitializer.java`: `getTypesToCreate`
- `intg/.../model/impexp/AtlasImportRequest.java`, `AtlasImportResult.java`

## Deviations

- **DV-125:** `importfile` reads only from the server's configured `import_folder`; Atlas reads any path the
  server can read.
- **DV-126:** an imported entity whose unique values a stored entity of another GUID holds keeps the stored
  GUID; Atlas renames the stored entity to the imported GUID and records the old one as historical. An entity
  that names one not yet written is written again itself; Atlas's retry moves its position past it.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__import_service.py` — IMS-02 to IMS-06: an export imported into
  a catalogue without its types, the type merge, a clash of values, the start position, the import folder.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_import.py` — IMS-01 and IMS-06 through the routes.
- `apps/aurelius-atlas-server/scenarios/admin/import.scenario.yaml` and the round trip in
  `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_export_e2e.py` — on Elasticsearch.
- `uv run aurelius-atlas-trace check`.

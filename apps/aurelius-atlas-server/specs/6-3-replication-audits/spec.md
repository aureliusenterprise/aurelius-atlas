# 6.3c2 Replication and the export/import audit trail

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-307, DV-130; relies on DD-304, the export of 6.3a and the import of 6.3b2

Each export and import that moves entities leaves an audit entry. One that replicates (the `replicatedTo`
or `replicatedFrom` option) records the other catalogue as an `AtlasServer` and marks each entity it moved
with that server. Two endpoints read them back. The admin audits (`admin/audits`,
`admin/audit/{guid}/details`) follow in 6.3c3.

## Scope

| Endpoint                                   | Needs                    |
| ------------------------------------------ | ------------------------ |
| `GET /api/atlas/admin/server/{serverName}` | the entity read (DD-307) |
| `GET /api/atlas/admin/expimp/audit`        | the entity read (DD-307) |

In `aurelius-atlas-model`, `AtlasServer`, `ExportImportAuditEntry` and the replication options in `impexp`. In
`aurelius-atlas-core`, `atlas_server_service`, `export_import_audit_service` and `audits_writer`, and their hooks
in `export_service` and `import_service`. In `aurelius-atlas-server`, the two routes in `routes/admin`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REP-01 | A server is an `AtlasServer` entity: `name`, `displayName`, `fullName` (unique), `additionalInfo` and `urls`. `GET admin/server/{serverName}` answers the one of that full name, with its GUID; none is `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` (404). Atlas asks no admin privilege; the read is an entity read                                                                                                                                                                                                                                     |
| REP-02 | After an export, and after an import unless its options name `migration`, this server (the `cluster_name` setting) is saved as a server of that name, then an `__ExportImportAuditEntry` is written of the user, the operation (`EXPORT`, `IMPORT`), the source and target server names, the start and end times and the result as JSON (an export's with its type definitions). An operation of no entity writes none; an import's result over 1 MiB is written without its `processedEntities`                                                      |
| REP-03 | An export's source is this server and its target the server the `replicatedTo` option names; an import's source is the one `replicatedFrom` names and its target this server. A full name `<data center>$<server>` names `<server>`; one without `$` names itself; no option names none. An operation that failed stops after its entry                                                                                                                                                                                                               |
| REP-04 | When the option is there, `skipUpdateReplicationAttr` is not `true` and entities moved, the other server is saved under its name and full name, its `additionalInfo.REPL_DETAILS` (a JSON map) giving the first entity's GUID the export's change marker; a `hive_table` or `hive_column` gives its `hive_db`'s GUID instead (0 removes the key). Each moved entity, and each it owns, that has the `replicatedTo` (export) or `replicatedFrom` (import) attribute gets the soft reference `AtlasServer:<guid>`, once, written straight to the entity |
| REP-05 | `GET admin/expimp/audit` takes `serverName`, `userName`, `operation`, `startTime`, `endTime`, `limit` and `offset`. It answers the entries each given value equals, `serverName` either end, as a basic search of `__ExportImportAuditEntry` with its limit and offset; an entry the user may not read is left out (DV-130)                                                                                                                                                                                                                           |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `getCluster`, `getExportImportAudit`
- `repository/.../impexp/AuditsWriter.java` (`ExportAudits`, `ImportAudits`, `ReplKeyGuidFinder`)
- `repository/.../impexp/AtlasServerService.java`, `ExportImportAuditService.java`
- `repository/.../ogm/AtlasServerDTO.java`, `ExportImportAuditEntryDTO.java`
- `repository/.../impexp/ExportService.java#updateSinkWithOperationMetrics`, `ImportService.java#processEntities`
- `intg/.../model/impexp/AtlasServer.java`, `ExportImportAuditEntry.java`
- `addons/models/0000-Area0/patches/001-base_model_replication_attributes.json`

## Deviations

- **DV-130:** `admin/expimp/audit` leaves out an entry the user may not read; Atlas fails on the scrubbed entry's
  missing times.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__replication_audits.py` — REP-01 to REP-05: a replicating
  export and import, the audit entries and their search, the size trim, the server names, the Hive key.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_replication.py` — REP-01, REP-04, REP-05
  through the routes.
- `apps/aurelius-atlas-server/scenarios/admin/replication.scenario.yaml` and
  `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_export_e2e.py` — on Elasticsearch.
- `uv run aurelius-atlas-trace check`.

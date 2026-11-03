# 6.3c3 Admin audits

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-308, DV-131; relies on DD-307 and the entity audits of 3.x

Atlas keeps a second audit trail beside the entity audits: an `__AtlasAuditEntry` for each purge, export,
import, change of the type definitions and start of the server. The dashboard's administration tab lists them
and, for a purge, the entities it removed. The aging of the entity audits (`admin/audits/ageout`) follows in
6.3c4.

## Scope

| Endpoint                                         | Needs                    |
| ------------------------------------------------ | ------------------------ |
| `POST /api/atlas/admin/audits`                   | `ADMIN_AUDITS`           |
| `GET /api/atlas/admin/audit/{auditGuid}/details` | the entity read (DD-308) |

In `aurelius-atlas-model`, `atlas_audit` (`AtlasAuditEntry`, `AuditOperation`, `AuditSearchParameters`). In
`aurelius-atlas-core`, `atlas_audit_service`, `request_context`, `typedef_change_listener`,
`typedef_audit_listener`, and the change listeners of `typedef_store`. In `aurelius-atlas-server`, the
routes and audits in `routes/admin`, the `RequestContextMiddleware` and the server's start audits in `app`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ADA-01 | An admin audit is an `__AtlasAuditEntry`: `userName`, `operation` (`PURGE`, `EXPORT`, `IMPORT`, `IMPORT_DELETE_REPL`, `TYPE_DEF_CREATE`, `TYPE_DEF_UPDATE`, `TYPE_DEF_DELETE`, `SERVER_START`, `SERVER_STATE_ACTIVE`), `params`, `startTime`, `endTime` (epoch milliseconds), `clientId`, `result` and `resultCount`, answered with its GUID and without its null fields                                                                                                                                                                                                                                                                                                                                                                      |
| ADA-02 | An entry names the request's user, else the process's login name, else `atlas`; the request's client address, else `<host name>:<address>` of this host; and runs from the request's start to now. A purge that purged entities records the GUIDs asked for (`[a, b]`) and the purged ones joined by commas, with their count. An export whose request has options and items records the options with `operationStatus`, and the items counted by type, with their count; `importData` records `operationStatus` and its export's items so, or without an export request the import's metrics and its count of entities. The server's start records `SERVER_START` from its start to now and `SERVER_STATE_ACTIVE` now, a failure only logged |
| ADA-03 | Each change of the type definitions that is written (a request's, an import's, the models' at start, a patch's) is told to the store's change listeners, a listener's failure only logged. The audit listener records `TYPE_DEF_CREATE`, `TYPE_DEF_UPDATE` and `TYPE_DEF_DELETE` of the definitions created, updated (less those also created, once each by name, in name order) and deleted: the kinds in the order they first come as `params`, the definitions by kind as JSON as `result`, their count as `resultCount`                                                                                                                                                                                                                   |
| ADA-04 | `POST admin/audits` takes `AuditSearchParameters` (`auditFilters`, `limit`, `offset`, `sortBy`, `sortOrder`) and needs `ADMIN_AUDITS`, `Admin Audits`. No body is `INVALID_PARAMETERS`, `Audit Search Parameters not specified`; a `sortBy` or a criterion on an attribute an entry lacks is `UNKNOWN_ATTRIBUTE`, `Attribute <name> not found for type Atlas Audit Entry`. The top-level criteria that have a value are searched under the filter's condition, as a basic search of `__AtlasAuditEntry`; an entry the user may not read is left out (DD-308)                                                                                                                                                                                  |
| ADA-05 | `GET admin/audit/{auditGuid}/details` reads the entity of the GUID (`INSTANCE_GUID_NOT_FOUND`; an entity read). For an entry with a result, the result's GUIDs from `offset` (0) up to `limit` (10) each give the entity header of their latest entity audit of the operation's action. Only `PURGE` has one (`ENTITY_PURGE`); any other operation is `INTERNAL_ERROR`, `Invalid operation for Entity Audit Event V2: <operation>`. An entry without a result answers `[]`                                                                                                                                                                                                                                                                    |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `getAtlasAudits`, `getAuditDetails`, `purgeByIds`,
  `addToExportOperationAudits`, `addToImportOperationAudits`, `auditImportExportOperations`
- `webapp/.../web/service/EmbeddedServer.java`: `auditServerStatus`
- `repository/.../audit/AtlasAuditService.java`, `TypeDefAuditListener.java`
- `repository/.../ogm/AtlasAuditEntryDTO.java`
- `repository/.../store/graph/AtlasTypeDefGraphStore.java`: `notifyListeners`
- `server-api/.../RequestContext.java`: `getCurrentUser`, `getClientIPAddress`, `getRequestTime`
- `intg/.../model/audit/AtlasAuditEntry.java`, `AuditSearchParameters.java`

## Deviations

- **DV-131:** an export or import item named by GUID alone is left out of the audit's counts by type; Atlas
  fails the request on the null type name after the export or import ran.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__atlas_audit_service.py` — ADA-01 to ADA-05: the request's
  user and client, the search and its refusals, a purge's details, the typedef audits and a failing listener.
- `libs/python/aurelius-atlas-model/tests/test__atlas_audit.py` — the models.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_admin_audits.py` — ADA-02 to ADA-05 through the
  routes: the start, a type change, a purge and its details, an export and an import.
- `apps/aurelius-atlas-server/scenarios/admin/admin-audits.scenario.yaml` and
  `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_admin_audits_e2e.py` — on Elasticsearch.
- `uv run aurelius-atlas-trace check`.

# 3.5a Entity audit

- **Status:** in progress
- **Pull request:** [#127](https://github.com/aureliusenterprise/aurelius-atlas/pull/127)
- **Records:** DD-082 to DD-084, DV-39, DV-40; relies on DD-049, DD-059

The first part of increment 3.5 (DD-082): an audit event for each entity a write, delete or purge creates,
changes, deletes or purges, kept in an index of its own, and Atlas's `GET v2/entity/{guid}/audit` to read them,
which is what the dashboards' audit tab calls. 3.5b adds the classification events and `bulk/headers`.

## Scope

| Endpoint                                | Takes                                                               | Answers                        |
| --------------------------------------- | ------------------------------------------------------------------- | ------------------------------ |
| `GET /api/atlas/v2/entity/{guid}/audit` | `startKey`, `auditAction`, `count`, `offset`, `sortBy`, `sortOrder` | a list of `EntityAuditEventV2` |

In `aurelius-atlas-model`, `audit` (`EntityAuditEventV2`, `EntityAuditActionV2`). In `aurelius-atlas-core`,
`entity_change_notifier` (`EntityChangeNotifier`: Atlas's `AtlasEntityChangeNotifier`), `entity_audit_listener`
(`EntityAuditListener`: `EntityAuditListenerV2`) and `entity_audit_repository` (`EntityAuditRepository` and its
Elasticsearch implementation: `HBaseBasedAuditRepository`); `testing/memory.py` gains
`InMemoryEntityAuditRepository`. The entity writer tells the notifier what it changed (DD-084). The server's
`routes/entity` answers the endpoint.

Not in scope:

| Not delivered here                                                                            | Delivered by |
| --------------------------------------------------------------------------------------------- | ------------ |
| Classification and propagated classification events; `bulk/headers` (DD-074)                  | 3.5b         |
| Term, label, business and custom attribute events (`TERM_*`, `LABEL_*`, `*_ATTRIBUTE_UPDATE`) | 5.2, 5.3     |
| Import events (`ENTITY_IMPORT_*`)                                                             | 6.3          |
| `admin/audits` (`AtlasAuditService`), audit age-out (`AtlasAuditReductionService`)            | –            |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUD-01 | `EntityAuditEventV2` reads and writes `entityId`, `timestamp` (epoch milliseconds), `user`, `action`, `details`, `eventKey`, `entity` and `type`, nulls included. Listed events have no `entity` and no `type`, as Atlas does not keep the entity definition (`atlas.audit.persistEntityDefinition=false`)                                                                                                                                                                                                                                                                                                                                |
| AUD-02 | After a write, delete or purge has committed, its response's entities are recorded (`onEntitiesMutated`): first `pruneResponse` takes from the created, updated and partially updated entities those `DELETED`, and from each list those a later kind names (purged over deleted, created, updated, partially updated; deleted over created, updated, partially updated; created over updated, partially updated; updated over partially updated); then the created, updated, partially updated, deleted and purged entities are recorded in that order, those of internal types left out                                                 |
| AUD-03 | A created entity records `ENTITY_CREATE` with the details `Created: <JSON>`, the JSON of the entity as read after the write without relationship attributes; an updated or partially updated one `ENTITY_UPDATE` with `Updated: <JSON>`, or `ENTITY_CREATE` with `Created: <JSON>` when it is incomplete and its create and update times are the same; a deleted one `ENTITY_DELETE` with `Deleted entity`; a purged one `ENTITY_PURGE` with `Purged: <JSON>`, the JSON of an entity made from its header (its type name, attributes, GUID, status, classifications and meanings, `isProxy` and `isIncomplete` false, `provenanceType` 0) |
| AUD-04 | Details longer than 1,048,576 UTF-8 bytes are written again without the entity's attributes and relationship attributes; still longer, with an entity of only its GUID, type name, create and update times and users, status and version                                                                                                                                                                                                                                                                                                                                                                                                  |
| AUD-05 | An event's `timestamp` is the time it is recorded, its `user` the request's, and its `eventKey` `<entityId>:<timestamp>:<index>:<now>`, `index` its position among the events of its kind of that request (DD-083)                                                                                                                                                                                                                                                                                                                                                                                                                        |
| AUD-06 | `GET {guid}/audit` needs an entity with the GUID, in any state, or an `ENTITY_PURGE` event of it; else it fails with `INSTANCE_GUID_NOT_FOUND`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| AUD-07 | With `sortBy` or an `offset` above -1, every event of the entity (of `auditAction` when given) is sorted by `user` or `action` (ignoring case, then by timestamp) or else by `timestamp`, the whole order reversed when `sortOrder` is `desc` in any case, events otherwise in the newest-key-first order; the answer is `count` events from `offset` (a negative offset reads as 0, a negative count as 100, a count of 0 as all)                                                                                                                                                                                                        |
| AUD-08 | Otherwise the events of the entity are answered newest key first (DD-083), from `startKey` on, that key included, when given; only those of `auditAction` when given; at most `count` (default 100), all for -1, none for any other negative count                                                                                                                                                                                                                                                                                                                                                                                        |
| AUD-09 | `auditAction` is an action's name or `TAG_ADD`, `TAG_DELETE`, `TAG_UPDATE` (Atlas's `fromString`; `CUSTOM_ATTRIBUTE_UPDATE` is not among them); `count` a Java `short`, `offset` an `int`. A value that is none of these fails with `BAD_REQUEST` (DV-39)                                                                                                                                                                                                                                                                                                                                                                                 |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `getAuditEvents`, `getEntityHeaderFromPurgedAudit`
- `repository/.../store/graph/v2/AtlasEntityChangeNotifier.java`: `onEntitiesMutated`, `pruneResponse`,
  `toAtlasEntities`
- `repository/.../audit/EntityAuditListenerV2.java`: `onEntitiesAdded`, `onEntitiesUpdated`, `onEntitiesDeleted`,
  `onEntitiesPurged`, `getAuditEventDetail`, `getV2AuditPrefix`
- `repository/.../audit/HBaseBasedAuditRepository.java`, `AbstractStorageBasedAuditRepository.java`,
  `InMemoryEntityAuditRepository.java`
- `intg/.../model/audit/EntityAuditEventV2.java`; `repository/src/test/.../audit/AuditRepositoryTestBase.java`

## Deviations

DV-39: a `count`, `offset` or `auditAction` that is not one fails in Atlas with Jersey's parameter error, which
its `AllExceptionMapper` answers as a `500` with a text body; Aurelius Atlas answers `BAD_REQUEST`. DV-40: Atlas
writes the events in the request before its graph commits, so a failed commit leaves events of a change that was
not made; Aurelius Atlas writes them after the change committed, so a process that stops in between loses them
(DD-082). As everywhere until 6.1, events have no user (DV-04).

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — AUD-01.
- `libs/python/aurelius-atlas-core/tests/` — AUD-02 to AUD-08 on the in-memory repository and the fake client.
- `libs/python/aurelius-atlas-core/e2e/` — events written and listed on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/entity/` — AUD-01, AUD-06 to AUD-09
  over HTTP.
- `uv run aurelius-atlas-trace check`.

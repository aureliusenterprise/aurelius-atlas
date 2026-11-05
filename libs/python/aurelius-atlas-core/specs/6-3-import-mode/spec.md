# 6.3b1 Import mode of the entity writer

- **Status:** done
- **Pull request:** to follow
- **Records:** DD-305, DV-123, DV-124; relies on DD-052, DD-061, DD-302

An Atlas import writes each exported entity through the normal entity write, with `isImportInProgress` set. That
flag changes about a dozen places in the write: what an export carries is kept rather than made anew, and what
a request would be refused or checked for is let through. This first half of 6.3b ports those branches into
`EntityWriter.create_or_update_for_import`, tested on its own. The import service that reads the ZIP, merges the
type definitions and serves `admin/import` follows in 6.3b2.

## Scope

No endpoint. In `aurelius-atlas-core`, `EntityWriter.create_or_update_for_import` and `with_system_attributes`;
the import branches of `EntityDiscovery`, `RelationshipMapper`, `EntityComparator`, `EntityChangeNotifier` and
`EntityAuditListener`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| IMP-01 | An import writes one exported entity with the entities it owns, as `createOrUpdate` does, its classifications and business attributes replacing the stored ones                                                                                                                                                                                                                    |
| IMP-02 | An imported entity keeps its version, create time, creator, home, proxy flag, provenance, custom attributes and labels as given. Its update time and updater are the import's, as `mapAttributes` sets them, unless it gives no attribute. A label it changes is audited, as setting labels is                                                                                     |
| IMP-03 | An imported entity with an assigned GUID that is not stored is created with that GUID; it is not looked up by its unique values. A reference to an assigned GUID that is not stored is no error                                                                                                                                                                                    |
| IMP-04 | An imported `DELETED` entity that is stored `ACTIVE` is deleted after the import's write; an imported `ACTIVE` entity that is stored `DELETED` is made `ACTIVE`, with its `DELETED` relationships to the entities its relationship attributes name, and is answered as created. An imported entity left incomplete, stored incomplete, is left as it is                            |
| IMP-05 | A reference that names its relationship type and relationship GUID creates the relationship with that GUID; a stored relationship is found by its label, not by the GUID. A reference to an entity that is not there is left out                                                                                                                                                   |
| IMP-06 | An import compares an entity's classifications and business attributes too: a given null differs from a stored empty list, as `Objects.equals` does. An updated entity's own classifications are removed, then the given ones of its own added (DD-305); a classification that says nothing about propagation does not propagate. Its business attributes are overwritten (BMD-04) |
| IMP-07 | An import's creates, updates and deletes are not checked against the user's privileges (AUZ-07 does not apply)                                                                                                                                                                                                                                                                     |
| IMP-08 | An import's entity events are `ENTITY_IMPORT_CREATE`, `ENTITY_IMPORT_UPDATE` and `ENTITY_IMPORT_DELETE`                                                                                                                                                                                                                                                                            |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `createOrUpdateForImport`, `createOrUpdate`,
  `preCreateOrUpdate` (the `isImportInProgress` branches)
- `repository/.../store/graph/v2/IDBasedEntityResolver.java`: `resolveEntityReferences`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `createVertexWithGuid`, `updateSystemAttributes`,
  `importActivateEntity`, `mapObjectIdValueUsingRelationship`, `updateRelationshipGuidForImport`,
  `addClassifications`, `deleteClassifications`, `setBusinessAttributes`
- `repository/.../store/graph/v2/AtlasEntityComparator.java`: the classification and business attribute sections
- `repository/.../audit/EntityAuditListenerV2.java`: `onEntitiesAdded`, `onEntitiesUpdated`, `onEntitiesDeleted`
  (`isImport`)

## Deviations

- **DV-123:** an import's classification events come after the entity's `ENTITY_IMPORT_UPDATE`; Atlas records
  them before it, in the same transaction (DD-305).
- **DV-124:** an imported shell entity (`isIncomplete`) that is not stored is created as a full entity; Atlas
  creates a shell vertex for it.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_import.py` — IMP-01 to IMP-08 on the in-memory documents.
- `uv run aurelius-atlas-trace check`.

# 6.2b Authorization: entities, classifications, relationships and the glossary

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-254; relies on DD-253, ADR 038 (accepted with 6.2c)

6.2a granted Atlas's privileges by four roles and checked the type definitions and the purge. This part makes
the checks Atlas's entity and relationship stores make, at the same points and with the same action texts:
reading, creating, updating and deleting entities, their classifications and the relationships between them.
The glossary and the saved searches are stored as entities and relationships, so they are checked through the
same stores, as Atlas's `DataAccess` and `GlossaryService` are. Labels and business metadata are not served yet;
their checks come with them in 5.3. Search results and lineage are scrubbed in 6.2c.

## Scope

| Endpoint                                                                                               | Needs                                                 |
| ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `GET /api/atlas/v2/entity/guid/{guid}`, `.../header`, `/bulk`, `/uniqueAttribute/...`, `/{guid}/audit` | `ENTITY_READ`                                         |
| `POST /api/atlas/v2/entity`, `/bulk`; `PUT .../uniqueAttribute/...`, `.../guid/{guid}`                 | `ENTITY_CREATE`, `ENTITY_UPDATE`                      |
| `DELETE /api/atlas/v2/entity/guid/{guid}`, `/bulk`, `/uniqueAttribute/...`                             | `ENTITY_DELETE`                                       |
| `GET .../classifications`, `.../classification/{name}`                                                 | `ENTITY_READ`                                         |
| `POST`, `PUT`, `DELETE` of classifications, `/bulk/classification`, `/bulk/setClassifications`         | `ENTITY_ADD_`, `_UPDATE_`, `_REMOVE_CLASSIFICATION`   |
| `POST`, `PUT`, `DELETE /api/atlas/v2/relationship`                                                     | `RELATIONSHIP_ADD`, `_UPDATE`, `_REMOVE`              |
| `/api/atlas/v2/glossary/...`, `/api/atlas/v2/search/saved/...`                                         | as the entities and relationships they read and write |

In `aurelius-atlas-core`, `authorization` (Atlas's privileges, the `Authorizer` a store is given, `Granted`,
the action text), and the checks in `EntityWriter`, `EntityClassifications`, `ClassificationAssociator`,
`RelationshipStore`, `DataAccess`, `GlossaryService`, `UserProfileService` and `EntityDiscoveryService`. In
`aurelius-atlas-server`, `authorization.authorizer` hands each request's stores its user's privileges, and the
entity routes check the reads Atlas's entity store checks.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUZ-07 | Creating or updating entities needs `ENTITY_CREATE` for each entity the request creates, `create entity: type=<type>`, then `ENTITY_UPDATE` for each it changes, `update entity: type=<type>`; an entity the request leaves unchanged is not checked. A partial update by unique attributes needs `update entity ByUniqueAttributes` once the entity is found, and setting one attribute `update entity ByUniqueAttributes : guid=<guid>` once it is found. Deleting needs `ENTITY_DELETE` for each entity found, `delete entity: guid=<guid>`, or `delete entity: typeName=<type>, uniqueAttributes={<name>=<value>}`; a missing one is skipped unchecked. Nothing is written when a check refuses. A store built without an authorizer checks nothing (DD-254) |
| AUZ-08 | Reading an entity's classifications needs `ENTITY_READ`, `get classifications: guid=<guid>` or `get classification: guid=<guid>, classification=<name>`, once the entity is found. Adding, updating and removing need `ENTITY_ADD_CLASSIFICATION`, `ENTITY_UPDATE_CLASSIFICATION` and `ENTITY_REMOVE_CLASSIFICATION` for each classification, `<add, update or remove> classification: guid=<guid>, classification=<name>`, before the classifications are validated; removing one propagated from another entity is not checked. Setting classifications reads the current ones unchecked, and a refused change makes its step `(Partial)`                                                                                                                      |
| AUZ-09 | Adding a relationship needs `RELATIONSHIP_ADD` once it is validated and found new, unless its type has a legacy attribute end, whose change is the entity's update; updating needs `RELATIONSHIP_UPDATE` once it is validated; removing needs `RELATIONSHIP_REMOVE` once it is found and not deleted. These checks name no action: the message ends after `is not authorized to perform`                                                                                                                                                                                                                                                                                                                                                                         |
| AUZ-10 | Glossary objects, profiles and saved searches are checked as the entities and relationships they are stored as: saving one as `AUZ-07`'s creates and updates, deleting one as its deletes, assigning a term as `AUZ-09`'s add; loading one needs `ENTITY_READ`, `read entity: guid=<guid>`, or for an object found by unique attributes `read entity: typeName=<type>, uniqueAttributes={...}`; listing glossaries needs it for each listed, `read entity: guid=<guid>`. A bulk load leaves out what it may not read                                                                                                                                                                                                                                             |
| AUZ-11 | Reading an entity, its header or its audit needs `ENTITY_READ` once it is found: `read entity: guid=<guid>` by GUID, `read entity: typeName=<type>, uniqueAttributes={...}` by unique attributes, `read entity: typeName=<type>, guid=<guid>` for each found by sets of them, and `read entity audit: guid=<guid>` for the audit of a purged entity. A missing entity is not found first                                                                                                                                                                                                                                                                                                                                                                         |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `getById`, `getHeaderById`, `getByIds`,
  `getByUniqueAttributes`, `getEntitiesByUniqueAttributes`, `createOrUpdate`, `updateByUniqueAttributes`,
  `updateEntityAttributeByGuid`, `deleteById`, `deleteByIds`, `deleteByUniqueAttributes`, `addClassifications`,
  `addClassification`, `updateClassifications`, `deleteClassification`, `getClassifications`, `getClassification`
- `repository/.../store/graph/v2/AtlasRelationshipStoreV2.java`: `createRelationship`, `updateRelationship`,
  `deleteById`
- `repository/.../store/graph/v2/ClassificationAssociator.java`: `Updater`
- `repository/.../ogm/DataAccess.java`, `repository/.../glossary/GlossaryService.java` (`getGlossaries`)
- `webapp/.../web/rest/EntityREST.java`: `getAuditEvents`

## Deviations

None. Atlas also checks `RELATIONSHIP_ADD` for each relationship an entity write creates; under DD-253 only
`atlas-write` grants it, together with the entity privileges checked first, so the outcome is the same (DD-254).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — AUZ-03, AUZ-07 to AUZ-10 at each store, with and without the privilege.
- `apps/aurelius-atlas-server/tests/` — AUZ-11 with tokens of no role and of `atlas-read`; a reader refused
  entity, glossary and saved-search writes.
- `apps/aurelius-atlas-server/e2e/` — the parity scenarios as the dev realm's writer, who holds every role.
- `uv run aurelius-atlas-trace check`.

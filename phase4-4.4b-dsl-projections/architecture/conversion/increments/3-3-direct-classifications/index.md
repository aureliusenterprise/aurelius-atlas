# 3.3a Direct classifications

- **Status:** in progress
- **Pull request:** [\#118](<https://github.com/aureliusenterprise/aurelius-atlas/pull/118>)
- **Records:** DD-070 to DD-073, DV-34, DV-35; relies on DD-043 to DD-049, DD-052, DD-056, DD-061, DD-062

The first part of increment 3.3 (DD-073; 3.3b brings `bulk/setClassifications` and `bulk/headers`): classifications attached directly to entities, through `EntityREST` and entity creates, read back with the entities.

## Scope

| Endpoint | Takes | Answers |
| --- | --- | --- |
| `GET /api/atlas/v2/entity/guid/{guid}/classifications` | – | `AtlasClassifications` |
| `GET /api/atlas/v2/entity/guid/{guid}/classification/{classificationName}` | – | `AtlasClassification` |
| `POST /api/atlas/v2/entity/guid/{guid}/classifications` | a list of `AtlasClassification` | nothing (`204`) |
| `PUT /api/atlas/v2/entity/guid/{guid}/classifications` | a list of `AtlasClassification` | nothing (`204`) |
| `DELETE /api/atlas/v2/entity/guid/{guid}/classification/{classificationName}` | – | nothing (`204`) |
| `POST`, `PUT /api/atlas/v2/entity/uniqueAttribute/type/{typeName}/classifications?attr:…` | a list of `AtlasClassification` | nothing (`204`) |
| `DELETE /api/atlas/v2/entity/uniqueAttribute/type/{typeName}/classification/{name}?attr:…` | – | nothing (`204`) |
| `POST /api/atlas/v2/entity/bulk/classification` | `ClassificationAssociateRequest` | nothing (`204`) |

Entity reads answer `classifications`, and headers `classificationNames` and `classifications`; an entity create attaches the classifications it gives; deletes delete an entity's classifications with it.

In `aurelius-atlas-model`, `AtlasClassifications` and `ClassificationAssociateRequest`. In `aurelius-atlas-core`, `stored_classification` (`StoredClassification`) and `entity_classifications` (`EntityClassifications`: the classification methods of `AtlasEntityStoreV2` and `EntityGraphMapper`); classification instances are documents of their own index, listed by the entity they are attached to (DD-070), written with entities all or nothing (DD-071). The server's `routes/entity` answers the endpoints.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `POST bulk/setClassifications` (`ClassificationAssociator`), `GET bulk/headers?tagUpdateStartTime` | 3.3b |
| Propagation: propagated classifications, `associatedEntityGuid`, propagation tasks (DV-34) | 3.4 |
| Classifications of updated entities in an import (`replaceClassifications`) | 6.3 |
| Audit events and notifications of classification changes | 3.5, – |
| Access checks (`ENTITY_ADD_CLASSIFICATION`, …) | 6.2 |

## Semantics

| Id | Rule |
| --- | --- |
| CLS-01 | `AtlasClassifications` is Atlas's `PList` of classifications: `list`, `startIndex` 0, `pageSize` and `totalCount` its length, `sortType` `NONE`. `ClassificationAssociateRequest` reads and writes `classification`, `entityGuids`, `entitiesUniqueAttributes` and `entityTypeName` |
| CLS-02 | An entity reads its classifications in `classifications`, in the order they were attached, absent when it has none (`mapClassifications`). Each has its `typeName`, every attribute of its type (null when it has no value), `entityGuid`, `entityStatus`, `propagate`, `removePropagationsOnEntityDelete`, and `validityPeriods` when stored (`toAtlasClassification`). A header has their names in `classificationNames` (ERD-07), and where ERD-07 and EWR-13 give `classifications`, them |
| CLS-03 | `GET guid/{guid}/classifications` answers the entity's classifications as `AtlasClassifications`; an unknown GUID fails with `INSTANCE_GUID_NOT_FOUND`. `GET guid/{guid}/classification/{name}` fails with `TYPE_NAME_INVALID` (`CLASSIFICATION`, name) for a name no classification type has, and answers the first classification of that name, ignoring case, attached directly (`entityGuid` empty or the entity's), else the first of the name; none fails with `CLASSIFICATION_NOT_FOUND`. A path parameter over 4096 characters fails with `INVALID_QUERY_PARAM_LENGTH` |
| CLS-04 | Adding classifications to an entity fails with `INVALID_PARAMETERS` (`Guid(s) not specified`, `classifications(s) not specified`) without a GUID or classifications, and with `INSTANCE_GUID_NOT_FOUND` for an unknown entity, in any state. Each classification is then checked and normalised by its type: `CLASSIFICATION_NOT_FOUND` for an unknown type, `INVALID_PARAMETERS` with the type's messages (validity periods included, EVL-07); then each fails with `INVALID_PARAMETERS` (`entity: <guid>, already associated with classification: <name>`) when the entity has one of its name attached directly, and with `INVALID_ENTITY_FOR_CLASSIFICATION` when its type may not classify the entity's type (THY-07) |
| CLS-05 | Each added classification, unless it says `propagate` and names another entity, is attached as a new classification instance: `propagate` true when not given (DD-072, DV-34), `removePropagationsOnEntityDelete` false when not given, `entityGuid` the entity's when not given, `entityStatus` `ACTIVE` when not given, its validity periods and its attributes as their types store them (DD-049). The entity's `updateTime` and `updatedBy` change. The request answers `204` |
| CLS-06 | The `uniqueAttribute` forms find the entity as ERD-08 and ERD-09 do: `TYPE_NAME_INVALID` (`ENTITY`) for an unknown entity type, `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` (type, values) when no `ACTIVE` entity holds the values; then they add, update or delete as the GUID forms do |
| CLS-07 | `bulk/classification` fails with `INVALID_PARAMETERS` (`no classification`) without a classification type name, and (`Need either list of GUIDs or entity type and list of qualified Names`) without GUIDs and without both the entity type and unique attribute sets. With both, it checks the type (`TYPE_NAME_INVALID`), adds the GUID of each set's `ACTIVE` holder, skipping sets that find none, and fails (`No guid found for given entity Type Name and list of attributes`) when there is then no GUID. It checks the classification once (CLS-04), each entity (`INSTANCE_GUID_NOT_FOUND`, the association checks) before changing any, then attaches it to each (CLS-05), all in one write |
| CLS-08 | Updating classifications fails with `INVALID_PARAMETERS` without a GUID (`Guid not specified`) or classifications, and with `INSTANCE_GUID_NOT_FOUND`; each is checked as CLS-04 checks it. Each, in turn: one naming another entity fails with `CLASSIFICATION_UPDATE_FROM_PROPAGATED_ENTITY`; one the entity has not attached directly with `CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY`; it is checked for update by its type (`CLASSIFICATION_NOT_FOUND`, `INVALID_PARAMETERS`); then its given attributes replace the stored ones, its validity periods, `propagate` and `removePropagationsOnEntityDelete` when given replace theirs, and the entity's `updateTime` and `updatedBy` change. A change of `propagate` propagates nothing until 3.4 (DV-34) |
| CLS-09 | `DELETE guid/{guid}/classification/{name}` fails with `TYPE_NAME_INVALID` for an unknown classification type, `INSTANCE_GUID_NOT_FOUND`, `NO_CLASSIFICATIONS_FOUND_FOR_ENTITY` when the entity has no classification attached directly, and `CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY` when none of them has the name (exactly). The instance is removed, whatever the delete type, and the entity's `updateTime` and `updatedBy` change. One naming another entity in `associatedEntityGuid` fails, until 3.4 brings propagated classifications, with `PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY` (name, that entity, the entity), as Atlas answers when it has none |
| CLS-10 | An entity create attaches the classifications the entity gives, after its attributes, as CLS-05 does, without CLS-04's checks: one of an unknown type fails with `CLASSIFICATION_NOT_FOUND` (DV-35). Its `CREATE` header is taken before they are attached, so it shows none (`constructHeader`). An update ignores them, as Atlas's `createOrUpdate` does without `replaceClassifications` |
| CLS-11 | Deleting an entity softly keeps its classifications, `entityStatus` `DELETED`; a hard delete and a purge remove them. A purge's headers have the purged entity's classifications (EDL-05) |
| CLS-12 | A classification type is in use while a classification instance of it exists, in any state: the typedef store refuses to delete it (`TYPE_HAS_REFERENCES`) |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: the classification methods, `ensureClassificationType`, `hasNoGUIDAndTypeNameAttributes`
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `getClassifications`, `getClassification`, `addClassifications`, `addClassification`, `updateClassifications`, `deleteClassification`, `validateAndNormalize`, `validateEntityAssociations`, `getClassificationNames`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `addClassifications`, `updateClassifications`, `deleteClassification`, `mapClassification`, `createClassificationVertex`, `validateAndNormalizeForUpdate`, `mapAttributesAndClassifications` (created entities)
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `toAtlasClassification`, `getAllClassifications`, `mapClassifications`, `mapVertexToAtlasEntityHeader`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `deleteAllClassifications`, `deleteEdge` (classification edges); `AtlasClassificationDefStoreV2#deleteByName`
- `intg/.../model/instance/AtlasClassification.java` (`AtlasClassifications`), `intg/.../model/PList.java`, `intg/.../model/instance/ClassificationAssociateRequest.java`

## Deviations

DV-34: Atlas propagates a classification with `propagate` true over the entity's relationships (by default as a deferred task); until 3.4 Aurelius Atlas stores `propagate` but propagates nothing, so no entity has a propagated classification for a delete naming `associatedEntityGuid` to remove. DV-35: an entity create giving a classification of an unknown type fails in Atlas with a `NullPointerException`; Aurelius Atlas answers `CLASSIFICATION_NOT_FOUND`.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/instance/` — CLS-01.
- `libs/python/aurelius-atlas-core/tests/` — CLS-02, CLS-04, CLS-05, CLS-07 to CLS-12 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — classifications written, read and deleted with entities on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/entity/` — CLS-03 to CLS-09 over HTTP.
- `uv run aurelius-atlas-trace check`.

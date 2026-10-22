# 1.4 Typedef store

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-028, DD-029, DD-030, DV-06; relies on ADR 047, DD-002, DD-005, DD-024

## Scope

Type definitions are kept in Elasticsearch and loaded into the type registry when the server starts, in a new library `libs/python/aurelius-atlas-core` (package `aurelius_atlas_core`, the `-core` layer of [DD-002](<https://aureliusenterprise.github.io/feat-webapp-details-components/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)):

- the typedef store: create, update and delete type definitions, with the checks Atlas's store makes and its registry does not (unique and well-formed names, no attribute removed, no type deleted while something refers to it), and the audit fields;
- the stored form: what Atlas keeps of a definition, which is what it answers with afterwards;
- persistence in one Elasticsearch document, written with optimistic concurrency ([DD-028](<https://aureliusenterprise.github.io/feat-webapp-details-components/architecture/conversion/design-log/#dd-028-the-type-definitions-are-one-elasticsearch-document>), [DD-029](<https://aureliusenterprise.github.io/feat-webapp-details-components/architecture/conversion/design-log/#dd-029-server-processes-share-the-type-definitions-through-the-documents-version>));
- the server loads the stored definitions into its registry at start-up and keeps it in step with other processes.

No endpoint changes: `/v2/types` arrives in 1.6.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Atlas's built-in models (`addons/models`), the model patches and `createUpdate` | 1.5 |
| `/v2/types/...`, search filters over type definitions, authorization of type reads | 1.6, 6.2 |
| Refusing to delete a type that entities or classifications still use | 2.2 (DD-030) |
| Attribute names that are DSL keywords (`atlas.types.allowReservedKeywords`) | not ported (\*) |

(\*) Atlas allows them by default; the check is off unless that setting is changed.

## Semantics

| Id | Rule |
| --- | --- |
| TDS-01 | Creating definitions resolves them with every stored type first (TRG-09); an unknown type name or GUID found then fails with `BAD_REQUEST` (400) carrying the resolution's message. Nothing is stored unless every definition passes |
| TDS-02 | A definition's name must match `[a-zA-Z][a-zA-Z0-9_ ]*`, optionally prefixed with `__`, else `TYPE_NAME_INVALID_FORMAT` (400); a name already stored fails with `TYPE_ALREADY_EXISTS` (409), and a name another kind holds with `TYPE_MATCH_FAILED` (400), naming Atlas's legacy kind (`CLASS`, `TRAIT`, `STRUCT`, …) |
| TDS-03 | A created definition gets `typeVersion` `1.0`, `version` 1, a random GUID and the current time as `createTime` and `updateTime`, each only when it has none; its `description` defaults to its name; `createdBy` and `updatedBy` are the current user (none until 6.1, DV-06) |
| TDS-04 | Every attribute must have a name and a type name (`MISSING_MANDATORY_ATTRIBUTE`); a type it names that is neither built in nor stored fails with `UNKNOWN_TYPE` (400). A struct needs attributes (`BAD_REQUEST`, `Missing attributes for structdef`); a business metadata attribute's name must match the type name pattern (`ATTRIBUTE_NAME_INVALID_CHARS`). An enum needs elements, and each element a value and an ordinal (`MISSING_MANDATORY_ATTRIBUTE`, `values` and `elementValue`) |
| TDS-05 | An attribute is stored in Atlas's form and read back from it: cardinality and counts become `isOptional`, `valuesMinCount` and `valuesMaxCount` as Atlas's multiplicity gives them (an optional single value reads 0 and 1, an unbounded list or set 2147483647); only `ownedRef` and `inverseRef` constraints are kept, in that order; options, default value, description, display name, search weight and index type are kept |
| TDS-06 | A stored relationship without a category is `ASSOCIATION`, and without `propagateTags` is `NONE`; its label and ends are kept as given |
| TDS-07 | Updating finds each definition by its GUID when it has one, else by its name (`TYPE_GUID_NOT_FOUND` or `TYPE_NAME_NOT_FOUND`, 404, mapped to `BAD_REQUEST` while resolving, as TDS-01). The name, the kind and the creation fields stay; blank fields keep their stored value; `version` goes up by one and `updateTime` and `updatedBy` are set |
| TDS-08 | An update may not remove an attribute (`ATTRIBUTE_DELETION_NOT_SUPPORTED`), change an attribute's type (`BAD_REQUEST`, `Data type update for attribute is not supported`) or add a mandatory one (`CANNOT_ADD_MANDATORY_ATTRIBUTE`); a relationship's name, category and ends may not change (`RELATIONSHIPDEF_INVALID_*_UPDATE`, with Java's text of the ends); a business metadata attribute may not lose applicable entity types (`APPLICABLE_ENTITY_TYPES_DELETION_NOT_SUPPORTED`); super types may not be removed (`SUPERTYPE_REMOVAL_NOT_SUPPORTED`), nor some of a classification's entity types (`ENTITYTYPE_REMOVAL_NOT_SUPPORTED`), though all of them may. A classification's entity types must be stored entity types, on create too (`CLASSIFICATIONDEF_INVALID_ENTITYTYPES`) |
| TDS-09 | Deleting finds each definition by GUID, else name, and fails with `TYPE_HAS_REFERENCES` (409) while another stored type refers to it as a super type, an attribute type or a classification's entity type, and an entity type with `TYPE_HAS_RELATIONSHIPS` (409) while a relationship ends on it. References from definitions deleted in the same request do not count, so a relationship and the types it ends on may be deleted together |
| TDS-10 | A change is written only after the transient registry resolved it, then committed to the registry; when the write fails, nothing is committed and the stored document is unchanged |
| TDS-11 | The stored definitions are one document whose Elasticsearch version guards every write: a write based on an older version fails, the process reloads and the change is retried once, else `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` (500) (DD-028, DD-029) |
| TDS-12 | At start-up the server loads the stored definitions into its registry, dropping a second definition with the same name and an `ownedRef` constraint on an attribute that refers to no entity type, as Atlas's `rectifyTypeErrorsIfAny` does; with nothing stored, the registry holds the built-in types only |
| TDS-13 | A process whose registry is older than the stored document reloads it before it changes types, and at least every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS` (default 5) before it answers |

## Java origin

Apache Atlas `release-2.4.0`, `repository/src/main/java/org/apache/atlas/repository/store/graph/`:

- `AtlasTypeDefGraphStore`: `init`, `createTypesDef`, `updateTypesDef`, `deleteTypesDef`, `deleteTypeByName`, `getByName`, `getByGuid`, `rectifyTypeErrorsIfAny`
- `v2/AtlasTypeDefGraphStoreV2` (`createTypeVertex`, `updateTypeVertex`, `vertexToTypeDef`, the reference edges), `v2/AtlasAbstractDefStoreV2`, `v2/AtlasEnumDefStoreV2`, `v2/AtlasStructDefStoreV2` (`toJsonFromAttribute`, `toAttributeDefFromJson`, `updateVertexPreUpdate`), `v2/AtlasClassificationDefStoreV2`, `v2/AtlasEntityDefStoreV2`, `v2/AtlasRelationshipDefStoreV2`, `v2/AtlasBusinessMetadataDefStoreV2`: the checks and the stored form; the JanusGraph vertices and edges are replaced by DD-028
- tests: `repository/src/test/java/org/apache/atlas/repository/store/graph/AtlasTypeDefGraphStoreTest.java`

## Deviations

DV-06: until 6.1 there is no login, so stored definitions have no `createdBy` and `updatedBy`. The JSON order of stored attributes and sets follows DD-021 and DD-027.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — TDS-01 to TDS-12 on the fake Elasticsearch client (`aurelius_atlas_store_es.testing.fake`), run by `nx test aurelius-atlas-core -c ci`.
- `libs/python/aurelius-atlas-core/e2e/` — TDS-10 to TDS-13 against the dev store, two stores sharing it.
- `apps/aurelius-atlas-server/tests/` — the registry is loaded at start-up (TDS-12).
- `uv run aurelius-atlas-trace check`.

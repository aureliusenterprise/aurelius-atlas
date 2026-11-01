# 2.2 Entity store

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-043 to DD-048, DV-14 to DV-16; relies on ADR 023, ADR 047, DD-028 to DD-031, DD-039 to DD-041

## Scope

The entities' storage in Elasticsearch, in `aurelius-atlas-core`: what `AtlasEntityStoreV2` and `EntityGraphMapper` keep in the graph, without the request logic around it, which 2.3 to 2.5 port. ADR 047 leaves the storage layout, the identifier strategy and the consistency model to the design log; this increment records them.

| Module | What it holds |
| --- | --- |
| `stored_entity` | `StoredEntity`: an entity as stored, its system properties and attribute values |
| `unique_key` | `UniqueKey`: one unique attribute value of one entity type, the id of its reservation |
| `entity_documents` | `EntityDocuments` and its Elasticsearch implementation: indices, reads, conditional writes, reservations, journal |
| `entity_store` | `EntityStore`: GUIDs, reads by GUID and unique attributes, all-or-nothing writes, recovery, type usage |
| `testing/memory` | `MemoryEntityDocuments`, for tests |

The server builds the entity store at start-up, recovers interrupted writes, and gives the typedef store its type usage check (DD-030). It also answers `GET /api/atlas/admin/patches`, promised by 1.5 (DD-031).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Reading entities over REST, with relationships and classifications (`EntityGraphRetriever`) | 2.3 |
| Creating and updating entities from requests: discovery, references, relationships (`EntityGraphMapper`) | 2.4 |
| Deleting entities: soft, hard and purge | 2.5 |
| Indexing attribute values for search (the attribute mapping) | 4.1 |
| A recorded migration mechanism for mapping changes that move data (ADR 023) | when first needed |

## Semantics

| Id | Rule |
| --- | --- |
| ENS-01 | Entities live in one index behind the alias `aurelius-atlas-entities`, one document per entity with the GUID as its id; its system properties are mapped for exact lookup, its attribute values are stored but not indexed until 4.1 (DD-043). Unique value reservations and the write journal have an index each, `aurelius-atlas-unique-values` and `aurelius-atlas-entity-journal`. Preparing the store creates what is missing and changes nothing that exists |
| ENS-02 | A new entity's GUID is a random UUID in its canonical lower-case form, as Java's `UUID.randomUUID()` (DD-044) |
| ENS-03 | An entity is stored with its GUID, type name, every super type name, state, `createTime` and `updateTime` in epoch milliseconds, `createdBy` and `updatedBy`, `version`, `isIncomplete`, `provenanceType`, `homeId`, labels, custom attributes and attribute values. Attribute values are stored under the attribute's qualified name (`Referenceable.qualifiedName`) as the codec writes them (DD-039). Creating sets both times to the request's time and the state to `ACTIVE`; `version` is the entity's own, never incremented by the store (`getEntityVersion`) |
| ENS-04 | Entities are read by GUID, one or many, as last written: a read never waits for an index refresh. An unknown GUID reads as nothing |
| ENS-05 | An `ACTIVE` entity holds one reservation for each unique attribute with a value: of its entity type, the attribute's qualified name and the normalised value (`PER_TYPE_UNIQUE`). A write that needs a value another entity holds fails, writing nothing, with an error naming the value and its holder; Atlas fails such a write with an internal error (`AtlasSchemaViolationException`), and 2.4 decides the answer to a request. A value is released when the entity changes it, or leaves `ACTIVE` (`removeProperty(uniquePropertyName)` on delete) (DD-045) |
| ENS-06 | An entity is found by unique attributes: the `ACTIVE` entity of the type holding every given unique value; else, for a type with sub types, of the first sub type that has one (`findByUniqueAttributes`). Values of attributes that are not unique, and null values, are ignored; none left finds nothing |
| ENS-07 | A write is a batch of new and changed entities, all or nothing (DD-046): every reservation and check is made before any entity is written; a failure during the write restores every entity written to its state before; a write interrupted by a crash is undone by the next recovery. A reader may see part of a write while it is being written (DV-16) |
| ENS-08 | A changed entity is written only over the state it was read in; another process's write in between fails the batch with a version conflict, for the caller to read again and retry (DD-047) |
| ENS-09 | A type is in use while an entity of it exists, in any state (`typeHasInstanceVertex`); the typedef store asks before deleting a type (DD-030, DD-048) |
| ENS-10 | `GET /admin/patches` answers `{"patches": [...]}`, the patch records of the typedef document (DD-031) sorted by id, each as `AtlasPatch` writes it; Atlas's Java patches are not among them (DV-14) |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v2/EntityGraphMapper.java`: `createVertex`, `createVertexWithGuid`, `getEntityVersion`, `mapPrimitiveValue` (unique properties); `graph/GraphHelper.java`: `createVertexWithoutIdentity` (state, times, users)
- `repository/.../store/graph/v2/AtlasGraphUtilsV2.java`: `findByUniqueAttributes`, `findByTypeAndUniquePropertyName`; `graph/GraphBackedSearchIndexer.java`: `UniqueKind.PER_TYPE_UNIQUE`; `store/graph/v1/DeleteHandlerV1.java`: unique properties removed on delete
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`, `GraphTransactionInterceptor`: one transaction per request
- `intg/.../type/AtlasStructType.java`: `UNIQUE_ATTRIBUTE_SHADE_PROPERTY_PREFIX`, `getVertexUniquePropertyName`
- `webapp/.../resources/AdminResource.java#getAtlasPatches`; `repository/.../patches/AtlasPatchRegistry.java#getAllPatches`

## Deviations

DV-14: Atlas also records its Java patches (`JAVA_PATCH_0000_001`, …), which repair JanusGraph and Solr indexes and have nothing to repair in Elasticsearch; `admin/patches` lists the typedef patches only. DV-15: an entity's `createdBy` and `updatedBy` name the logged-in user in Atlas; until 6.1 they are absent, as for type definitions (DV-04, DV-06). DV-16: Atlas commits a request's entities in one graph transaction, which no reader sees half done; here a reader may see part of a multi-entity write for the duration of its bulk request (DD-046).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — ENS-02 to ENS-09 on the in-memory documents, including injected failures at each step of a write.
- `libs/python/aurelius-atlas-core/e2e/` — ENS-01, ENS-05, ENS-07 and ENS-08 against the dev store: two stores racing for a unique value, a write interrupted part-way and recovered.
- `apps/aurelius-atlas-server/scenarios/admin/patches.scenario.yaml` — ENS-10.
- `uv run aurelius-atlas-trace check`.

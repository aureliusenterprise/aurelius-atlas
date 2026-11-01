# 5.3d Business metadata in search

- **Status:** in progress
- **Pull request:** to follow
- **Records:** relies on DD-088, DD-302

5.3b stores business attribute values with the entity (DD-302). This last part of 5.3 lets basic search find them. A value is indexed as a search field under the attribute's qualified name, `<business metadata>.<attribute>`, like an entity attribute's. Basic search then takes that name in its entity filters, its sort and its requested attributes, for one entity type or for all of them, as Atlas's `getBusinesAAttribute` resolves it.

## Scope

| Endpoint | Needs |
| --- | --- |
| `GET`, `POST /api/atlas/v2/search/basic` | `<bm>.<attr>` in `entityFilters`, `sortBy`, `attributes` |
| `GET /api/atlas/v2/search/attribute`, `quick` | as basic search |

In `aurelius-atlas-core`, `search_fields` indexes business attributes. In `aurelius-atlas-typesystem`, the entity root resolves business attributes through the registry that resolved it last.

## Semantics

| Id | Rule |
| --- | --- |
| BMS-01 | An entity's business attribute values are search fields, kept current with each write, as its attributes' are |
| BMS-02 | Basic search takes a business attribute by its qualified name, `<business metadata>.<attribute>`, wherever it takes an attribute's name: an entity filter, `sortBy`, and `attributes`, whose answer names it so. For a named entity type, the business metadata must apply to it; for `_ALL_ENTITY_TYPES`, any business metadata's attribute is taken. A name that resolves to none is `UNKNOWN_ATTRIBUTE` |

## Java origin

Apache Atlas `release-2.4.0`:

- `intg/.../type/AtlasEntityType.java`: `getAttribute`, `getBusinesAAttribute`, `AtlasRootEntityType#getBusinessAttribute`
- `repository/.../graph/GraphBackedSearchIndexer.java`: the index of each business attribute's vertex property
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `mapVertexToAtlasEntityHeader` (requested attributes)

## Deviations

None.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_business_metadata.py` — BMS-01 and BMS-02 on the in-memory documents.
- `apps/aurelius-atlas-server/scenarios/entity/entity-business-metadata.scenario.yaml` — a basic search filtering on and answering a business attribute, on Elasticsearch in the e2e suite.
- `uv run aurelius-atlas-trace check`.

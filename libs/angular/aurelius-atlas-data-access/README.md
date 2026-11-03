# aurelius-atlas-data-access

Typed Angular data layer: the Atlas REST client (typedefs, admin, search,
lineage) and the client
for the Aurelius example backend (HTTP + SSE), with the TypeScript types mirroring
each API contract.

Part of the template **spine**.

## API

- `TypeDefsService` — the Atlas type-definition endpoints (`/atlas/v2/types/**`):
  searches, by-name/by-guid lookups (any kind and per kind), create/update/delete —
  `TypesREST` of Apache Atlas, served by `aurelius-atlas-server`
- `AdminService` — `version`, `status`, and this session's UI settings, the
  liveness/readiness texts, the patch records, purge, export/import, and the
  task list (`/atlas/admin/**`) — `AdminREST` of server 2.x/5.x (APC-02,
  AAC-01..07); the twin of `AtlasClient.admin` (CL-11, CLW-01..06)
- `LineageService` — the lineage endpoints (`/atlas/v2/lineage/**`): the
  lineage graph of an entity, its on-demand form with per-guid constraints,
  and the graph of the entity a unique attribute names — `LineageREST` of
  server 5.x (ALN-01..04); the twin of `AtlasClient.lineage` (CL-61..63)
- `RelationshipService` — the relationship endpoints (`/atlas/v2/relationship/**`):
  create and update (the bare relationship both ways), the always-wrapped read,
  and the soft/hard delete with its `deleteType` — `RelationshipREST` of server
  2.x (AREL-01..04); the twin of `AtlasClient.relationship` (CLR-01..04)
- `AtlasEntitiesService` — the entity endpoints (`/atlas/v2/entity/**`): the
  by-guid/by-unique-attribute reads (with the ext-info flags), their header
  siblings, the bulk reads, the audit events, and the changed-classification
  headers (8.17); the create/update, partial updates, and soft/hard deletes
  (8.18, AEW-01..06); and the classification, business-metadata (with the
  template download and file import), and label routes (8.19, ACL-01..09) —
  all thirty-seven `EntityREST` routes of server 2.3/7.6 (DET-03); the twin
  of `AtlasClient.entity` (CLE-01..CLE-12)
- `GlossaryService` — the glossary endpoints (`/atlas/v2/glossary/**`): the
  glossary routes (8.20, AGL-01..07) — the paged list, create/update/
  partial-update/delete, the detailed read, the paged category and term
  reads (full and header form), and the template download and file import —
  the term routes (8.21, AGT-01..06) — the term reads/creates/updates, the
  partial update, the delete, the related-terms map, and the paged
  assigned-entities read with its assignment trio — and the category routes
  (8.22, AGC-01..04) — the category read, its paged terms, its related
  map, create/update/partial-update/delete — all thirty-two `GlossaryREST`
  routes of server 2.4 (GLS/GTM/GTA/GCT/GIM); the twin of
  `AtlasClient.glossary` (CLG-01..CLG-09)
- `atlas-impexp.ts` / `atlas-mutation.ts` / `atlas-patches.ts` /
  `atlas-tasks.ts` — the export/import, mutation-response, patch-record, and
  task DTOs with the server's camelCase wire names, mirrored by hand from
  `libs/python/aurelius-atlas-model` (`impexp.py`, `instance/`, `patches.py`,
  `tasks.py`)
- `atlas-lineage.ts` — the lineage DTOs (`AtlasLineageInfo`,
  `LineageOnDemandConstraints`, …), mirrored by hand from
  `aurelius_atlas_model/lineage.py`
- `atlas-relationship.ts` — the relationship DTOs (`AtlasRelationship`,
  `AtlasRelationshipWithExtInfo`, `RelationshipStatus`), mirrored by hand from
  `aurelius_atlas_model/instance/relationship.py`
- `atlas-glossary.ts` — the glossary DTOs (`AtlasGlossary`,
  `AtlasGlossaryCategory`, `AtlasGlossaryTerm`, `AtlasGlossaryExtInfo`,
  `AtlasRelatedObjectId`, the header types, `GlossarySort`), mirrored by hand
  from `aurelius_atlas_model/glossary.py` and `instance/related_object_id.py`
- `atlas-audit.ts` — the entity-audit DTOs (`EntityAuditEventV2`,
  `EntityAuditActionV2`, `EntityAuditType`), mirrored by hand from
  `aurelius_atlas_model/audit.py`
- `atlas-entity.ts` — the entity DTO cluster (`AtlasEntity`, the
  ext-info wrappers, `AtlasClassification` and its `AtlasClassifications`
  `PList`, `ClassificationAssociateRequest`, `TimeBoundary`), mirrored by
  hand from `aurelius_atlas_model/instance/`
- `SearchService` — the search endpoints (`/atlas/v2/search/**`): the basic
  search (POST/GET), attribute, full-text, the quick search with its facets
  (POST/GET), term suggestions, the DSL search, and the seven saved-search
  routes — `DiscoveryREST` of increments 4.1–4.5 (APC-11, ACS-01..06, DD-217);
  no screen calls the new methods yet, 7.4's search slice is its first
- `atlas-profile.ts` — the saved-search DTOs (`AtlasUserSavedSearch`,
  `SavedSearchType`) with the server's camelCase wire names, mirrored by hand
  from `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/profile.py`)
- `atlas-typedef.ts` — the typedef DTO cluster (`AtlasTypesDef` and friends) with the
  server's camelCase wire names, mirrored by hand from
  `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/typedef.py`)
- `atlas-error.ts` — the Atlas error body (`errorCode`/`errorMessage`/`errorCause`,
  SRV-04) and its extractor
- `EntitiesService` — CRUD and search against the FastAPI example
  (`/entities/*`), plus `GET /entities/sse` live updates via
  `ngx-sse-client` (auto-reconnecting, cleaned up on destroy)
- `API_BASE_URL` / `provideApiBaseUrl()` — the base URL the API is reachable under
  (defaults to `/api`); consuming apps provide it from their runtime config
- `Entity` — the domain type mirroring `libs/python/aurelius-atlas-example`
- `Envelope<T>`, `PaginatedResponse<T>`, `FindAllQueryParams` — API response and
  query shapes

## Usage

```ts
import { EntitiesService, provideApiBaseUrl, TypeDefsService, type Entity } from "aurelius-atlas-data-access";

private readonly entities = inject(EntitiesService);
private readonly typedefs = inject(TypeDefsService);

// In the app's environment providers (defaults to "/api" if omitted):
provideApiBaseUrl(config.apiBaseUrl);

// The Atlas surface (APC-02): searches, lookups, create/update/delete of typedefs.
this.typedefs.getTypedefs({ excludeInternalTypesAndReferences: true });
```

> [!NOTE]
> `Entity` here and the Python `Entity` model are kept in sync by hand — update
> both when the domain model changes. The same applies to the typedef DTOs in
> `atlas-typedef.ts` and `aurelius_atlas_model/typedef.py` (APC-03), and to the
> search DTOs in `atlas-search.ts` and `aurelius_atlas_model/discovery.py`, and
> to the saved-search DTOs in `atlas-profile.ts` and
> `aurelius_atlas_model/profile.py`, and to the admin DTOs in
> `atlas-impexp.ts`/`atlas-mutation.ts`/`atlas-patches.ts`/`atlas-tasks.ts` and
> `aurelius_atlas_model/impexp.py`/`instance/`/`patches.py`/`tasks.py`, and to
> the lineage DTOs in `atlas-lineage.ts` and `aurelius_atlas_model/lineage.py`,
> to the relationship DTOs in `atlas-relationship.ts` and
> `aurelius_atlas_model/instance/relationship.py`, to the entity and audit
> DTOs in `atlas-entity.ts`/`atlas-audit.ts` and
> `aurelius_atlas_model/instance/`/`audit.py`, and to the glossary DTOs in
> `atlas-glossary.ts` and `aurelius_atlas_model/glossary.py`/
> `instance/related_object_id.py`.

## Testing

```bash
nx test aurelius-atlas-data-access -c ci   # Vitest unit tests
```

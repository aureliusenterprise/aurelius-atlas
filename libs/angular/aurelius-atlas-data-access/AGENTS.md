# aurelius-atlas-data-access

Typed Angular data layer: the Atlas REST client (`TypeDefsService`, `AdminService`)
against `aurelius-atlas-server`, and the client for the FastAPI example backend.
This file covers wiring specific to this lib; workspace-wide rules live in the root
`AGENTS.md` and the Angular lib recipe in `libs/angular/AGENTS.md`.

## Layout

The Atlas API clients live in `src/lib/atlas/` — one subfolder per backend
contract, so future API clients (the example backend today, others tomorrow)
stay separated from the Atlas surface. `src/index.ts` re-exports everything;
consumers import from the package root only, never a subfolder path.

- `src/lib/atlas/type-defs.service.ts` — `TypeDefsService` (`/atlas/v2/types/**`, TYR-01..10)
- `src/lib/atlas/search.service.ts` — `SearchService` (`/atlas/v2/search/**`, APC-11,
  ACS-01..06): the basic/attribute/fulltext/quick searches, the suggestions, the
  DSL search and the seven saved-search routes of server 4.1–4.5;
  GET parameters drop the Java defaults, as the routes read an absent parameter;
  `getSavedSearches` keeps the server's 204 as a `null` body (DD-314)
- `src/lib/atlas/admin.service.ts` — `AdminService` (`/atlas/admin/**`, ADM-01..05,
  AAC-01..07): version/status/session, the liveness/readiness texts, the patch
  records, purge, export/import, and the task list — the twin of
  `AtlasClient.admin` (CL-11, CLW-01..06); `export` answers the
  `{ body, contentType }` pair of DD-315 where the twin returns a tuple
- `src/lib/atlas/atlas-entities.service.ts` — `AtlasEntitiesService`
  (`/atlas/v2/entity/**`, DET-03 — the 2.3+7.6 wiring's client, DD-187)
- `src/lib/atlas/atlas-typedef.ts` — the typedef DTO cluster with the server's camelCase
  wire names (APC-03); `src/lib/atlas/atlas-search.ts` — the search DTO cluster
  (`SearchParameters`, `AtlasSearchResult`, `AtlasQuickSearchResult`, …);
  `src/lib/atlas/atlas-profile.ts` — the saved-search DTOs (`AtlasUserSavedSearch`,
  `SavedSearchType`, SVS-01); `src/lib/atlas/atlas-entity.ts` — the entity DTOs
  (with `AtlasObjectId`); `src/lib/atlas/atlas-impexp.ts` — the export/import DTOs
  and `AtlasExportAnswer` (DD-315); `src/lib/atlas/atlas-mutation.ts` —
  `EntityMutationResponse`; `src/lib/atlas/atlas-patches.ts` / `atlas-tasks.ts` —
  the patch/task DTOs; `src/lib/atlas/atlas-error.ts` — the Atlas
  error body (SRV-04, APC-04), shared with `entities.service.ts`
- `src/lib/entities.service.ts` — `EntitiesService` (HTTP + SSE) and the example API
  types — the FastAPI example's client, outside the Atlas folder by design;
  `src/index.ts` is the public API
- `src/lib/api-config.ts` — `API_BASE_URL` injection token (root default `/api`) and
  `provideApiBaseUrl()`; every service builds all URLs from it (APC-01)
- `.spec.ts` files colocated with source

## Wiring Checklist

- `tsconfig.base.json` — `aurelius-atlas-data-access` path alias used by the frontend.
- The Atlas contract: the typedef/admin/search endpoints and their DTOs must
  match `apps/aurelius-atlas-server/aurelius_atlas_server/routes/{types,admin,discovery}.py`
  and `libs/python/aurelius-atlas-model` **by hand** — when the Python model changes,
  update `atlas-typedef.ts` / `atlas-search.ts` too (increments 7.3, 7.4's client
  half per DD-217, spec `libs/angular/aurelius-atlas-data-access/specs/7-3-api-client-auth/spec.md`).
- The search wire contract has a Python twin: `AtlasClient.search` (CL-13,
  CSD-01..06) in `libs/python/aurelius-atlas-server-client` reads the same
  routes and models — change the endpoints on both sides in the same PR. The
  saved-searches 204 reads as `None` on the Python side and a `null` body here
  (CSD-03 ↔ ACS-03, DD-314).
- The admin wire contract has the same twin: `AtlasClient.admin` (CL-11,
  CLW-01..06) covers the same twelve routes of `routes/admin.py` — change them
  on both sides in the same PR. `export` returns `(bytes, content-type)` there
  and answers the typed `AtlasExportAnswer` pair here (CLW-03 ↔ AAC-04,
  DD-315). On the plain-text health routes the twin parses the Atlas error
  body from the raw bytes (CL-04); here a text request keeps its error body as
  text and the caller parses it (AAC-01).
- The example-backend contract: endpoints (`/entities/*`, `/entities/sse`),
  `Envelope<T>`, and `PaginatedResponse<T>` must match
  `apps/aurelius-atlas-fastapi-example`.
- `Entity` mirrors `libs/python/aurelius-atlas-example` **by hand** — when the Python
  model changes, update this type too (see that lib's AGENTS.md for the full
  ripple list).
- `package.json` — peer deps: Angular `^22` (the workspace), `ngx-sse-client ^21`
  (its own peer range allows it).

## Commands

```bash
nx test aurelius-atlas-data-access -c ci   # Vitest unit tests
nx build aurelius-atlas-data-access        # ng-packagr-lite package build
```

## Conventions

- Every backend endpoint gets a typed method here — components never call
  `HttpClient` directly.
- New response shapes go in the types file next to `Entity`, exported from
  `src/index.ts`.
- SSE stays on `ngx-sse-client` with cleanup on destroy; don't hand-roll
  `EventSource`.

## Removal

Part of the spine. Removing it means removing the `aurelius-atlas-data-access` alias and
all imports in `aurelius-atlas-frontend-example` (its components would need their own
HTTP calls), plus its `mkdocs.yaml` entries.

# aurelius-atlas-data-access

Typed Angular data layer: the Atlas REST client (`TypeDefsService`, `AdminService`)
against `aurelius-atlas-server`, and the client for the FastAPI example backend.
This file covers wiring specific to this lib; workspace-wide rules live in the root
`AGENTS.md` and the Angular lib recipe in `libs/angular/AGENTS.md`.

## Layout

- `src/lib/type-defs.service.ts` — `TypeDefsService` (`/atlas/v2/types/**`, TYR-01..10)
- `src/lib/admin.service.ts` — `AdminService` (`/atlas/admin/**`, ADM-01/02/05)
- `src/lib/atlas-typedef.ts` — the typedef DTO cluster with the server's camelCase
  wire names (APC-03); `src/lib/atlas-error.ts` — the Atlas error body (SRV-04, APC-04)
- `src/lib/entities.service.ts` — `EntitiesService` (HTTP + SSE) and the example API
  types; `src/index.ts` is the public API
- `src/lib/api-config.ts` — `API_BASE_URL` injection token (root default `/api`) and
  `provideApiBaseUrl()`; every service builds all URLs from it (APC-01)
- `.spec.ts` files colocated with source

## Wiring Checklist

- `tsconfig.base.json` — `aurelius-atlas-data-access` path alias used by the frontend.
- The Atlas contract: the typedef/admin endpoints and the typedef DTOs must match
  `apps/aurelius-atlas-server/aurelius_atlas_server/routes/{types,admin}.py` and
  `libs/python/aurelius-atlas-model` **by hand** — when the Python model changes,
  update `atlas-typedef.ts` too (increment 7.3, spec
  `docs/architecture/conversion/increments/7-3-api-client-auth.md`).
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

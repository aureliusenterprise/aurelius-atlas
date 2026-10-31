# aurelius-atlas-data-access

Typed Angular data layer: the Atlas REST client (typedefs, admin, search,
entities) with the TypeScript types mirroring each API contract. The FastAPI
example's client went with the example apps (ADR 050, DD-019).

Part of the template **spine**.

## API

- `TypeDefsService` — the Atlas type-definition endpoints (`/atlas/v2/types/**`):
  searches, by-name/by-guid lookups (any kind and per kind), create/update/delete —
  `TypesREST` of Apache Atlas, served by `aurelius-atlas-server`
- `AdminService` — `version`, `status`, and this session's UI settings
  (`/atlas/admin/**`)
- `SearchService` — the search endpoints (`/atlas/v2/search/**`): the basic
  search (POST/GET), attribute, full-text, the quick search with its facets
  (POST/GET), and term suggestions — `DiscoveryREST` of increments 4.1/4.2
  (APC-11, DD-217); no screen calls it yet, 7.4's search slice is its first
- `atlas-typedef.ts` — the typedef DTO cluster (`AtlasTypesDef` and friends) with the
  server's camelCase wire names, mirrored by hand from
  `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/typedef.py`)
- `atlas-error.ts` — the Atlas error body (`errorCode`/`errorMessage`/`errorCause`,
  SRV-04) and its extractor
- `API_BASE_URL` / `provideApiBaseUrl()` — the base URL the API is reachable under
  (defaults to `/api`); consuming apps provide it from their runtime config

## Usage

```ts
import { provideApiBaseUrl, TypeDefsService } from "aurelius-atlas-data-access";

private readonly typedefs = inject(TypeDefsService);

// In the app's environment providers (defaults to "/api" if omitted):
provideApiBaseUrl(config.apiBaseUrl);

// The Atlas surface (APC-02): searches, lookups, create/update/delete of typedefs.
this.typedefs.getTypedefs({ excludeInternalTypesAndReferences: true });
```

> [!NOTE]
> The typedef DTOs in `atlas-typedef.ts` mirror
> `aurelius_atlas_model/typedef.py` (APC-03) and the search DTOs in
> `atlas-search.ts` mirror `aurelius_atlas_model/discovery.py` — kept in sync
> by hand, update both when the domain model changes.

## Testing

```bash
nx test aurelius-atlas-data-access -c ci   # Vitest unit tests
```

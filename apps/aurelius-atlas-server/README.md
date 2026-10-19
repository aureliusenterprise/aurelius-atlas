# aurelius-atlas-server

The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API, implemented in Python on Elasticsearch
([ADR 046](../../docs/architecture/adr/046-the-catalogue-keeps-its-public-contract.md),
[ADR 047](../../docs/architecture/adr/047-one-search-store-is-the-system-of-record.md)).

Introduced by increment 0.5 with the admin endpoints; every later increment adds the endpoints of its
Atlas resource. What is ported, and how, is tracked in the
[conversion ledger](../../docs/architecture/conversion/index.md).

## Endpoints

| Endpoint                         | Answers                                                              |
| -------------------------------- | -------------------------------------------------------------------- |
| `GET /api/atlas/admin/version`   | Name, release and revision of the server                             |
| `GET /api/atlas/admin/status`    | `{"Status": "ACTIVE"}` while the server runs                         |
| `GET /api/atlas/admin/session`   | The dashboard's settings and the user (no login until 6.1)           |
| `GET /api/atlas/admin/liveness`  | `Service is live` while the server runs                              |
| `GET /api/atlas/admin/readiness` | `Service is ready to accept requests` while Elasticsearch is healthy |
| `/api/atlas/v2/types/...`        | The type definitions: read, search, create, update and delete        |

## Dashboards

The server also serves the Apache Atlas 2.4.0 dashboards from
[`aurelius-atlas-dashboard`](../aurelius-atlas-dashboard/README.md): `dashboardv2` at `/` and
`dashboardv3` at `/n/`. The API is matched first. The image contains them; outside the image,
`AURELIUS_ATLAS_SERVER_DASHBOARD_DIR` names the built directory, and without it only the API is served.

## Type definitions

At start-up the server loads the type definitions stored in Elasticsearch (the `aurelius-atlas-typedefs`
index) into its type registry, through [`aurelius-atlas-core`](../../libs/python/aurelius-atlas-core/README.md).
It checks for another process's type change at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS`
(default 5). Then it loads Apache Atlas's built-in models and applies their patches, as Atlas does from
`$ATLAS_HOME/models`: by default the 2.4.0 models shipped with the server, or the directory
`AURELIUS_ATLAS_SERVER_MODELS_DIR` names, laid out as Atlas's. Only new types, newer `typeVersion`s and patches
not applied before change anything, so a restart writes nothing.

The 26 endpoints of Atlas's `TypesREST` (`aurelius_atlas_server/routes/types.py`) read and change the
definitions through that store. `GET typedefs` and `typedefs/headers` take Atlas's filter parameters (`type`,
`name`, `servicetype`, `supertype`, their `not` forms and `excludeInternalTypesAndReferences`) and list each kind
sorted by name (DD-034).

## Running it

```bash
npx nx serve aurelius-atlas-server   # builds the dashboards, starts the dev store and observability; https://localhost:21000
```

The server does not start without its store. Settings are environment variables prefixed
`AURELIUS_ATLAS_SERVER_`; see `aurelius_atlas_server/settings.py` for the full list.

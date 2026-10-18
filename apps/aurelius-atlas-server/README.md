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

## Dashboards

The server answers the API only. The Apache Atlas 2.4.0 dashboards come from
[`aurelius-atlas-dashboard`](../aurelius-atlas-dashboard/README.md): its nginx image serves
`dashboardv2` at `/` and `dashboardv3` at `/n/`, and keeps the API on the same origin by proxying
`/api/` here (DD-034). `nx up aurelius-atlas-dashboard` runs the whole product.

## Type definitions

At start-up the server loads the type definitions stored in Elasticsearch (the `aurelius-atlas-typedefs`
index) into its type registry, through [`aurelius-atlas-core`](../../libs/python/aurelius-atlas-core/README.md).
It checks for another process's type change at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS`
(default 5). Then it loads Apache Atlas's built-in models and applies their patches, as Atlas does from
`$ATLAS_HOME/models`: by default the 2.4.0 models shipped with the server, or the directory
`AURELIUS_ATLAS_SERVER_MODELS_DIR` names, laid out as Atlas's. Only new types, newer `typeVersion`s and patches
not applied before change anything, so a restart writes nothing. The `/v2/types` endpoints arrive in 1.6.

## Running it

```bash
npx nx serve aurelius-atlas-server   # the API: starts the dev store and observability; https://localhost:21000
npx nx up aurelius-atlas-dashboard   # the dashboards in front of that API; https://localhost:8080
```

The server does not start without its store. Settings are environment variables prefixed
`AURELIUS_ATLAS_SERVER_`; see `aurelius_atlas_server/settings.py` for the full list.

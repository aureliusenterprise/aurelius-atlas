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

## Running it

```bash
npx nx serve aurelius-atlas-server   # starts the dev store and observability first; https://localhost:21000
```

The server does not start without its store. Settings are environment variables prefixed
`AURELIUS_ATLAS_SERVER_`; see `aurelius_atlas_server/settings.py` for the full list.

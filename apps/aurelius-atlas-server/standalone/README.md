# Standalone server

The server image alone, with the Apache Atlas 2.4.0 dashboards, behind one nginx entry on port 9000. It is a
way to try the server by hand. `nx serve` and the e2e stacks are unchanged.

| Path                             | Service                                                    |
| -------------------------------- | ---------------------------------------------------------- |
| `https://localhost:9000/atlas2/` | The server and its dashboards; `/` redirects here          |
| `https://localhost:9000/auth/`   | The stack's own Keycloak with the dev realm, and its admin |

The store is the dev Elasticsearch. Keycloak is the stack's own, because the dev Keycloak's address is the
issuer the other dev services trust (DD-363); it imports the dev realm at every start.

## Start

The dev store runs first. The secrets come from the server's `.env` and the dev Keycloak's `.env`:

```bash
docker compose -f dev/elasticsearch/docker-compose.yaml up -d
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env up -d
```

The dashboards answer at <https://localhost:9000/atlas2/> once Keycloak is ready, about a minute after the
start. Sign in as `aurelius-writer` or `aurelius-reader`, with `DEV_USER_WRITER_PASSWORD` or
`DEV_USER_READER_PASSWORD` from the dev Keycloak's `.env`. Keycloak's admin console is
<https://localhost:9000/auth/admin/>, as `KC_BOOTSTRAP_ADMIN_USERNAME`. The certificate is the dev CA's, so
the browser asks once, for `localhost:9000`.

The image is `aurelius-atlas-server:local`; `npx nx docker-build aurelius-atlas-server` builds it from the
checkout.

## A sample dataset

`SAMPLE_ZIP` names an Apache Atlas export ZIP in `data/atlas-sample/` at the repository root. Once the server
is ready, the `sample-import` service signs in as `aurelius-writer` and posts it to `admin/import`, through
the proxy. Without `SAMPLE_ZIP`, or when no file has that name, the option is ignored: the service logs why
and exits, and the server runs as without it.

```bash
SAMPLE_ZIP=sample_data.zip docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env up -d
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml logs -f sample-import
```

The server creates the m4i types of the samples at start-up (ADR 058), so an import creates none. The log ends
with the import's status and its counts by type; a failed import exits non-zero. An import updates the
entities it finds by GUID, so running it again is safe. Other settings:

| Variable                | Default              | What it sets                                                         |
| ----------------------- | -------------------- | -------------------------------------------------------------------- |
| `SAMPLE_ZIP`            | empty: ignored       | The ZIP's file name in the sample folder                             |
| `SAMPLE_DIR`            | `data/atlas-sample/` | The sample folder; a relative path is read from this directory       |
| `SAMPLE_IMPORT_REQUEST` | `{}`                 | Atlas's `AtlasImportRequest` as JSON, such as its `options`          |
| `ATLAS_TASKS_ENABLED`   | `true`: as Atlas     | Whether the task worker propagates classifications after the request |

An import's propagation runs once it ends (DD-361), so an entity shows what is propagated to it a little
later.

## How it fits together

- `nginx.conf`: TLS on port 9000 with the server's certificate. `/atlas2/` goes to the server without the
  prefix; the server knows it as `AURELIUS_ATLAS_SERVER_ROOT_PATH`, so its redirects and its sign-in's return
  lead back under it (9.5). `/auth/` goes to Keycloak unchanged, which serves under `/auth` itself.
- The server and the sample import run in the proxy's network (`network_mode: service:proxy`). nginx reaches
  the server on `127.0.0.1:21000`, and the server reaches Keycloak at `https://localhost:9000/auth`, the
  address the browser uses, so the tokens' issuer is the one the server checks.

## Stop

```bash
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env down
```

The data stays in the dev store, as everything `nx serve` writes there does.

# Standalone server

The server image alone, with the Apache Atlas 2.4.0 dashboards, on the dev Elasticsearch and the dev Keycloak.
It is a way to try the server by hand. `nx serve` and the e2e stacks are unchanged.

## Start

The dev store and identity provider run first; the server's secrets come from its `.env`:

```bash
docker compose -f dev/elasticsearch/docker-compose.yaml up -d
docker compose -f dev/keycloak/docker-compose.yaml up -d
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env up -d
```

The dashboards answer at <https://localhost:21001/>. Sign in as `aurelius-writer` or `aurelius-reader`, with
`DEV_USER_WRITER_PASSWORD` or `DEV_USER_READER_PASSWORD` from the server's `.env`. The certificates are the
dev CA's, so the browser asks once for `localhost:21001` and once for `keycloak.localhost:8443`.

The image is `aurelius-atlas-server:local`; `npx nx docker-build aurelius-atlas-server` builds it from the
checkout.

## A sample dataset

`SAMPLE_ZIP` names an Apache Atlas export ZIP in `atlas_sample_data/` at the repository root. Once the server
is ready, the `sample-import` service signs in as `aurelius-writer` and posts it to `admin/import`. Without
`SAMPLE_ZIP`, or when no file has that name, the option is ignored: the service logs why and exits, and the
server runs as without it.

```bash
SAMPLE_ZIP=sample_data.zip docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env up -d
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml logs -f sample-import
```

The log ends with the import's status and its counts by type; a failed import exits non-zero. An import
updates the entities it finds by GUID, so running it again is safe. Other settings:

| Variable                | Default              | What it sets                                                         |
| ----------------------- | -------------------- | -------------------------------------------------------------------- |
| `SAMPLE_ZIP`            | empty: ignored       | The ZIP's file name in the sample folder                             |
| `SAMPLE_DIR`            | `atlas_sample_data/` | The sample folder; a relative path is read from this directory       |
| `SAMPLE_IMPORT_REQUEST` | `{}`                 | Atlas's `AtlasImportRequest` as JSON, such as its `options`          |
| `ATLAS_TASKS_ENABLED`   | `true`: as Atlas     | Whether the task worker propagates classifications after the request |

An import's propagation runs once it ends (DD-361), so an entity shows what is propagated to it a little
later.

## Stop

```bash
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml down
```

The data stays in the dev store, as everything `nx serve` writes there does.

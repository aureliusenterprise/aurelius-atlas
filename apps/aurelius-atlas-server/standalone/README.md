# Standalone server

The server image with the Apache Atlas 2.4.0 dashboards and the Aurelius Atlas webapp, behind one nginx entry
on port 9000. It is a way to try them by hand. `nx serve` and the e2e stacks are unchanged.

| Path                             | Service                                                     |
| -------------------------------- | ----------------------------------------------------------- |
| `https://localhost:9000/`        | The Aurelius Atlas webapp, in English or Dutch              |
| `https://localhost:9000/atlas2/` | The server and its Atlas dashboards                         |
| `https://localhost:9000/auth/`   | The stack's own Keycloak with the demo realm, and its admin |

The store is the stack's own Elasticsearch, so it holds what you import and nothing the e2e suites or
`nx serve` write to the dev store (DD-367). Keycloak is the stack's own too, because the dev Keycloak's
address is the issuer the other dev services trust (DD-363). At every start it imports the realm `demo` from
`keycloak/demo.json`, with three users (DD-366):

| User        | Roles                                                     | May                                                                   |
| ----------- | --------------------------------------------------------- | --------------------------------------------------------------------- |
| `atlas`     | `atlas-read`, `atlas-write`, `atlas-types`, `atlas-admin` | Everything: the catalogue, the types, import, export and purge        |
| `steward`   | `atlas-read`, `atlas-write`                               | Read and change the entities, their relationships and classifications |
| `scientist` | `atlas-read`                                              | Read the types and the entities                                       |

Their passwords are `DEMO_USER_ATLAS_PASSWORD`, `DEMO_USER_STEWARD_PASSWORD` and `DEMO_USER_SCIENTIST_PASSWORD`
in the dev Keycloak's `.env`, decrypted from its `.env.enc`.

## Start

The secrets come from the server's `.env` and the dev Keycloak's `.env`. The store uses the dev store's
configuration and certificate, `dev/elasticsearch/certs/`, and the webapp its own, `apps/aurelius-atlas-webapp/certs/`.
On a new clone, `npx nx certgen aurelius-atlas-dev-elasticsearch` and `npx nx certgen aurelius-atlas-webapp`
make them.

```bash
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env up -d
```

The webapp answers at <https://localhost:9000/> and the dashboards at <https://localhost:9000/atlas2/> once
Keycloak is ready, about a minute after the start. Sign in to either as one of the demo users; one sign-in
serves both, as they share the realm. Keycloak's admin console is <https://localhost:9000/auth/admin/>, as
`KC_BOOTSTRAP_ADMIN_USERNAME`, in the realm `master`; its session doesn't sign you in to the dashboards. The
certificate is the dev CA's, so the browser asks once, for `localhost:9000`.

The images are `aurelius-atlas-server:local` and `aurelius-atlas-webapp:local`; `npx nx docker-build
aurelius-atlas-server` and `npx nx docker-build aurelius-atlas-webapp` build them from the checkout.

## A sample dataset

`SAMPLE_ZIP` names an Apache Atlas export ZIP in `data/atlas-sample/` at the repository root. Once the server
is ready, the `sample-import` service signs in as `atlas` and posts it to `admin/import`, through
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
- `elasticsearch`: one node with `dev/elasticsearch/config/elasticsearch.yml`, the volumes
  `elasticsearch-data` and `elasticsearch-snapshots`, and no published port. The server reaches it as
  `https://elasticsearch:9200` with its own password, which is the `elastic` user's here.
- `/` and every other path go to the webapp's own nginx, which passes `/api/` on to the server unchanged.
  `webapp-config` fills that nginx's template into the volume `webapp-nginx-conf` before it starts
  (`webapp/resolve-nginx.sh`, as the chart's init container does), and `webapp/config.json` points the webapp
  at the demo realm. The stack has no telemetry collector, so `/otel/` takes the webapp's pushes and drops
  them.
- The server, the webapp and the sample import run in the proxy's network (`network_mode: service:proxy`).
  nginx reaches the server on `127.0.0.1:21000` and the webapp on `127.0.0.1:8080`, and the server reaches
  Keycloak at `https://localhost:9000/auth`, the
  address the browser uses, so the tokens' issuer is the one the server checks.

## Stop

```bash
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env down
```

The data stays in the stack's volumes for the next start. `down -v` deletes them, so the next start begins
with an empty store: the server creates Atlas's and the m4i types again, and `SAMPLE_ZIP` imports the sample.
The Statistics chart fills from the hourly snapshots, so a new store's chart is empty until the first full
hour.

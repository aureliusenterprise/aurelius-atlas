# aurelius-atlas-server

The Atlas REST API on Elasticsearch (DD-015, DD-016). This file covers wiring specific to this app;
workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

- `aurelius_atlas_server/app.py` — `create_app`: the store's lifetime, the error handler, the routers;
  `mount_dashboards`: the built dashboards after the routers (DD-018)
- `aurelius_atlas_server/settings.py` — `ServerSettings` (`AURELIUS_ATLAS_SERVER_` prefix)
- the lifespan in `app.py` opens the store, loads the type registry through `TypedefStore` (TDS-12), then
  the models of `models_dir` through `ModelLoader` (MDL-16); `app.state.type_registry` and
  `app.state.typedef_store` hold them. Tests set `models_dir` to an empty directory (`tests/conftest.py`),
  since Atlas's models take seconds to load; only the MDL-16 test loads them
- `aurelius_atlas_server/task_worker.py` — `TaskWorker`: started by the lifespan when `tasks_enabled`, woken
  by the entity store's `task_listeners` and polling every `task_poll_seconds` (DD-080). Tests and the e2e
  server run with tasks disabled so responses show propagation at once (DD-081); `tests/test__*_tasks.py`
  turns them on and runs on the module loop, where the lifespan started the worker
- `aurelius_atlas_server/embedding.py` — `EmbeddingClient` (an OpenAI-compatible `/v1/embeddings`, the
  embedder of 11.2) and `EmbeddingWorker`: with `embedding_url` set, the lifespan maps the entities' vectors,
  moving an entity index stored before to one that keeps vectors (DD-439), and the worker runs
  `EntityEmbeddingIndexer` rounds every `embedding_poll_seconds` (VEC-07, DD-436). While `app_search_enabled`,
  the indexer waits for an entity's App Search document, whose names join its text (EMC-04, DD-540). Unset,
  nothing changes (VEC-08). `tests/test__aurelius_atlas_server_embedding.py` mocks the embedder's transport
- `aurelius_atlas_server/app_search.py` — `AppSearchWorker`: unless `app_search_enabled` is false, the
  lifespan starts it on the entity documents, and it runs `AppSearchIndexer` rounds every
  `app_search_poll_seconds`, deriving the original webapp's missing and stale App Search documents (ASU-06,
  DD-521), each followed by a `QualityIndexer` round deriving the quality results and score totals (ASQ-07,
  DD-529) and a `GovernanceIndexer` round judging the governance verdicts (ASG-06, DD-535).
  The unit tests' settings turn it off so no round writes beside their requests;
  `tests/test__aurelius_atlas_server_app_search.py` turns it on
- `aurelius_atlas_server/snapshot_watcher.py` — `SnapshotWatcher`: with `snapshot_enabled` the lifespan puts
  the store's snapshot policy and starts it; it logs failed runs and reports the gauge
  `aurelius_atlas.snapshot.last_success` (SNP-01 to SNP-03, 6.4e)
- `aurelius_atlas_server/snapshots.py` — the command `python -m aurelius_atlas_server.snapshots
list|take|restore`, reading `StoreAccessSettings` alone; the chart's restore Job runs it (SNP-04, SNP-05,
  SNP-07). Its e2e rehearsal runs two ES containers of its own, never the dev store
- `aurelius_atlas_server/errors.py` — `AtlasError`, `AtlasErrorCode`, the Atlas error body and JSON media
  type; a 5xx answer is opaque and carries the trace id as `requestId` (SRV-07, DD-235)
- `aurelius_atlas_server/security_headers.py` — `SecurityHeadersMiddleware`: security headers on every
  answer, split `/api` path vs dashboard; HSTS gated on `hsts_enabled` (SRV-08, DD-236). TLS material
  is a required setting — the server never serves plaintext (SRV-06, DD-234)
- OTLP ingest (DD-196) lives in the shared `aurelius-atlas-otel` lib (DD-197):
  `app.py::_telemetry` maps `ServerSettings.otel_*` (`_ingest_source`) into
  `build_otlp_pipeline` and `build_otlp_log_processor`, installed by the lib's
  `setup_telemetry` on the native OTel providers (DD-210: the app owns its
  export; the static env headers cannot carry a 60s JWT). `BRIDGED_LOGGERS`
  send their records to the collector and still to stdout (OBS-01, DD-320)
- `e2e/load.py` + `e2e/test__aurelius_atlas_server_load_e2e.py` — the load test
  (LOD-01..03, DD-321), run with the e2e suite; `AURELIUS_ATLAS_LOAD_*` tune it
- `aurelius_atlas_server/authentication.py` — `AuthenticationMiddleware`, `SessionStore`, `user_of`: each
  request's user from its bearer token or browser session, the 401 or sign-in redirect, the CSRF check (6.1a,
  DD-250); `oidc_client.py` — `OidcClient`: the confidential client's code flow, refresh and sign-out;
  `routes/login.py` — `login.jsp` and `logout.html`. Tokens are verified by `aurelius-atlas-auth`
- `aurelius_atlas_server/root_path.py` — `site_path`, `under_root`: the server under a proxy's path prefix,
  uvicorn's `root_path` from `AURELIUS_ATLAS_SERVER_ROOT_PATH` (9.5, DD-363); the path checks read within it,
  the redirects lead under it
- `aurelius_atlas_server/tenancy.py` — `Tenancy`, `tenant_of`, `tenant_roles`: with `tenancy_enabled` (off by
  default; the chart's `tenancy` values and the standalone stack's `ATLAS_TENANCY_ENABLED` offer it, WPT-08,
  WPT-10), `user_of` reads the request's one tenant from the token's
  organization claim and its roles from that organization's groups, or refuses with 403 (TEN-01 to TEN-07,
  ADR 063). The tenant is on `request.state.tenant` and the core's `RequestContext` (TEN-08)
- `aurelius_atlas_server/tenant_stores.py` — `TenantStores`, `open_stores`, `stores`: the default store set and,
  with tenancy on, each provisioned tenant's (`aurelius-atlas-tenant-<alias>-*`), opened at start, or on its
  first request when provisioned later, and kept in `app.state.tenant_stores` (TSS-03, TSS-04, TPR-08). **A
  route reads its stores through `stores(request)`**, never from `app.state`, which names the default set's for
  the single-tenant tests alone (TSS-06, DD-570); the import and export lock is the store set's too (WPT-06).
  `TenantStoreSets` calls back as a store set opens and before it closes, which starts and stops its workers.
  A new index of a store set joins `STORE_SUFFIXES`, or removal leaves it behind (DD-574); a test fails until
  it does
- `aurelius_atlas_server/tenants.py` — `TenantsIndex`, `TenantDirectory`: the tenants' records in
  `aurelius-atlas-tenants` and the provisioned tenants the server reads from them, again every
  `tenancy_refresh_seconds` (TPR-01, TPR-07, DD-575). Tests record tenants with the `record_tenants` fixture
- `aurelius_atlas_server/tenant_workers.py` — `WorkerFactory`, `TenantFollower`: each open store set's task,
  App Search and embedding workers, audit aging and metrics history, the embedding client shared; with tenancy
  on, the tenants index read in the background to open and close store sets without a request (WPT-01 to
  WPT-04, DD-576, DD-577). A new background worker starts in `WorkerFactory.started`, never in `app.py`, or
  the tenants go without it
- `aurelius_atlas_server/provisioning.py` — the command `python -m aurelius_atlas_server.provisioning
provision|trust|list|remove`, reading the server's settings: a tenant's indices, models and sample made by the
  server's own start sequence and import, its record kept (TPR-02 to TPR-06, DD-573);
  `provision --existing-ok` is what the chart's hook Job runs (WPT-07, DD-579)
- `aurelius_atlas_server/authorization.py` — the four roles of the server's client that grant Atlas's
  privileges, `authorizer` and `verify_access` (6.2, DD-300). Every core store a route builds must be given
  `authorizer=authorizer(request)`: a store without one checks nothing (DD-301)
- `aurelius_atlas_server/routes/` — one router module per Atlas resource class (`admin.py` ← `AdminResource`);
  `app_search.py` is the original webapp's App Search API, answered by core's `AppSearchEngine` over
  `app.state.entity_documents` in App Search's shapes, refusals included, for each engine of core's `ENGINES`
  (ASE-01, ASE-02, ASQ-01, ASG-01, DD-527, DD-531, DD-534)
- `aurelius_atlas_server/__main__.py` — the uvicorn entry point
- `scenarios/` — parity scenarios, one directory per Atlas resource; run by `tests/` and `e2e/`
- `tests/` — unit tests on a fake Elasticsearch client; `e2e/` — the image over HTTPS on the dev store
- `helm/` — the `atlas-server` chart (its own section below)

## Porting an Atlas resource

1. Write the increment's spec, then the scenarios under `scenarios/<resource>/`, each citing the
   `release-2.4.0` code it was read from (ADR 052; the source is at `github.com/apache/atlas`).
2. Add `routes/<resource>.py` and include its router in `app.py`. Raise `AtlasError` with an
   `AtlasErrorCode` member copied from Atlas's `AtlasErrorCode` (status, code and message template).
3. Add the Java class to `docs/architecture/conversion/java-map.md`; every visible difference goes to
   `deviations.md` and into the scenario as a `deviations` entry.

## Wiring Checklist

- `project.json` — `implicitDependencies` and `serve` `dependsOn` (dev Elasticsearch,
  **dev Keycloak**, observability, the dashboard build — Keycloak joins for DD-196: the
  OTLP export mints its ingest JWT from the issuer, so `serve` needs it up).
  `docker-build` and `docker-publish` repeat the plugin's `dependsOn` and add the dashboard
  build: the plugin only chains the dependencies' `docker-build`, which the dashboard has not.
- OTLP export is app-owned (DD-196): `ServerSettings.otel_*` (`otel_token_url`,
  `otel_client_id`=`otel-atlas-server`, `otel_client_secret`,
  `otel_endpoint`=`https://localhost:4319`, `otel_ca_file`) — **not** the
  `OTEL_EXPORTER_*` env (static headers cannot carry the dev realm's 60s token).
  With no `otel_token_url`/`otel_client_secret` the server logs telemetry only
  (no OTLP), so the un-instrumented dev path stays zero-config.
- `.env.enc` — dev settings; the Elasticsearch password mirrors `dev/elasticsearch/.env`. Re-run
  `nx encrypt aurelius-atlas-server` after changing `.env`.
- `tls.json` — the server's certificate (`nx certgen`), used by `serve` and `e2e`.
- `Dockerfile` — installs the wheel `nx build` makes, with the workspace libraries bundled in, and copies
  the built dashboards (`aurelius-atlas-dashboard/dist`).
- `e2e/docker-compose.yaml` — the image on the dev store's network, reached as `elasticsearch:9200`.
  Its OTLP export uses the shim settings; the mint rides the TLS `:8443`
  issuer, pinned to `/certs/ca.pem` (DD-202: every producer mints there, the
  collector validates both listeners), so the server needs `extra_hosts:
keycloak.localhost:host-gateway` and the `otel-atlas-server` client imported
  (a long-lived dev Keycloak needs a recreate for a new client — see
  dev/keycloak/AGENTS.md).
- Authentication (6.1a, DD-250): `AURELIUS_ATLAS_SERVER_AUTH_*` name the dev Keycloak's master realm and the
  server's confidential client `aurelius-atlas-server` (`dev/keycloak/import/master.json`); its secret is
  `ATLAS_SERVER_CLIENT_SECRET` in `dev/keycloak/.env.enc`, mirrored as
  `AURELIUS_ATLAS_SERVER_AUTH_CLIENT_SECRET` here and in the webapp's `.env.enc`. The e2e suite mints the
  writer's tokens with `DEV_USER_WRITER_PASSWORD` and publishes the server on `127.0.0.1:21001`, the client's
  registered e2e return. Unit tests use the fake provider in `tests/fake_issuer.py`.

## Commands

```bash
npx nx serve aurelius-atlas-server
npx nx test aurelius-atlas-server -c ci
npx nx e2e aurelius-atlas-server -c ci    # builds the image, starts the dev store
uv run pytest apps/aurelius-atlas-server/tests
```

## Helm chart

`helm/` — the `atlas-server` chart (10.3a, CHT-20/21/22): the Deployment and
ClusterIP Service on 21000 with **HTTPS** probes (the server never serves
plaintext, SRV-06); every settings value naming a peer is a join — the store
Service (`ELASTICSEARCH_HOSTS` + its password Secret), the issuer URL (the
OTLP token-URL join), the CA/TLS file paths on the whole-Secret mount of the
chart's own `Certificate` (SANs = Service name + FQDNs, which is exactly what
the webapp's nginx pins with `proxy_ssl_name`). `telemetry.enabled` is off by
default — with it on, the collector leg joins (`:4319`, client `otel-atlas-server`,
Secret `atlas-otel-clients`; the join key is the client id on the prod realm,
the shared `OTEL_INGEST_CLIENT_SECRET` on `global.realm=master` — CHT-90,
DD-277). 10.12 adds the **auth block** (CHT-108, 6.1a's required settings):
`AUTH_SERVER_URL`/`_AUTH_REALM` join the issuer and `global.realm`,
`_AUTH_CLIENT_ID`/`_AUTH_AUDIENCES` are the `auth` values block (default
`aurelius-atlas-server` + `["aurelius"]`), `AUTH_CLIENT_SECRET` joins
`<release>-server-client` (`credentialSecrets.serverClient` brings your own),
`AUTH_CA_FILE` rides the Certificate's mounted ca.crt — and because
`AUTH_SERVER_URL` has no default in the app, the issuer guard fails an
authless render. `forwardedAllowIps` feeds `FORWARDED_ALLOW_IPS`
— stock render is loopback-only; the environment overlays name the pod CIDRs
(the two-hop client-IP trust, DD-261/CHT-32). The chart renders standalone
(test values) and through the umbrella (`helm/`); the chart-contract tests are
`tests/test__charts_server.py`. 10.6 adds the ingress allow (CHT-65): 21000
from the webapp and lineage-model pods only (`networkPolicy.peers.*` rename
the pod-name labels); the dashboard's gateway allow belongs to the umbrella.
Chart conventions and gotchas: `helm/AGENTS.md`.

```bash
npx nx run aurelius-atlas-server:helm-template
```

Removing the app removes `helm/` too — plus the umbrella's dependency and
values-toggle rows (`helm/AGENTS.md`).

## Removal

Not removable: this is the product.

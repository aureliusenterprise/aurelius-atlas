# aurelius-dev-governance

OpenMetadata data-governance stack (catalog + OpenLineage lineage graph).
This file covers wiring specific to this project; workspace-wide rules live in
the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — OpenMetadata server + its own Postgres (5433) and
  Elasticsearch. `nx up`/`serve` starts this stack (and, via
  `implicitDependencies` on `aurelius-dev-kafka`, the Kafka chain beneath it:
  observability → keycloak → kafka).
- `integrations/docker-compose.yaml` — the OpenLineage ingestion loop (separate
  stack, separate compose project): consumes `openlineage-events` from Kafka
  every 60s and writes the lineage into the server. Start it after the server.
- `integrations/openlineage.yaml` — the ingestion pipeline config (Kafka
  OpenLineage source). Its `sslConfig` values are `/certs/...` paths that the
  entrypoint renders to certificate content before each run.
- `config/metrics-puller.yaml` — OTel Collector config for the
  `metrics-puller` sidecar: scrapes Elasticsearch and the metadata Postgres
  and pushes OTLP to dev/observability (see Wiring Checklist).
- `.env` / `.env.enc` — SOPS-encrypted dev settings; `certs/` — mTLS material
  from `nx certgen` (gitignored).
- `Dockerfile` — the derived server image: hardened `dhi.io/openmetadata`
  base + the OpenTelemetry Java agent baked in (`ADD --checksum`, pinned
  version/SHA-256). Built by the `docker-build` target as `ghcr.io/
aureliusenterprise/aurelius-dev-governance:local`; `up`/`serve` build it
  automatically (compose plugin `dependsOn`).

## Wiring Checklist

- Server images are the hardened `dhi.io/openmetadata` (Docker Hardened
  Images) — the server through the derived `Dockerfile` above, whose
  `OM_VERSION` build arg the `docker-build` target resolves from
  `OPENMETADATA_VERSION` (so a bump rebuilds the derived image on the new
  base); the ingestion image stays `openmetadata/ingestion` (DHI publishes
  no hardened ingestion image). Keep both versions in sync — the ingestion
  client refuses to talk across major versions.
- Postgres and Elasticsearch are hardened too (`dhi.io/postgres`,
  `dhi.io/elasticsearch`) and serve TLS only:
    - Postgres follows the `dev/postgres` pattern — scram-sha-256, certs
      copied to `/tmp` with mode 600 at startup, and the shared
      `../postgres/pg_hba.conf` (hostssl-only). The metadata DB runs 18;
      OpenMetadata requires >= 15.
    - Elasticsearch runs with `xpack.security.enabled=true` + TLS on HTTP and
      transport and the `elastic` bootstrap password (`ES_PASSWORD`). Two DHI
      quirks: its entrypoint has no env2yaml, so every ES setting is passed as
      an `-E` command flag — otherwise Elastic's auto-configuration generates
      its own CA and ignores the mounted certs; and ES 9's entitlement
      framework only reads SSL material from the config directory, so
      `ca.pem`/`elasticsearch.pem`/`elasticsearch-key.pem` are bind-mounted
      individually into `/usr/share/elasticsearch/config`. The image also
      ships no data directory, so `elasticsearch-init` (root) fixes the named
      volume's ownership before the node starts.
    - The server/migrate containers mount `./certs` and connect with
      `DB_PARAMS=sslmode=verify-full&sslrootcert=/certs/ca.pem` and
      `ELASTICSEARCH_SCHEME=https` + truststore (`ELASTICSEARCH_TRUST_STORE_*`,
      PKCS12 holding the local root CA).
- Auth is Keycloak OIDC (`dev/keycloak`): the `openmetadata` client secret
  must match `OIDC_CLIENT_SECRET` here (both read the same
  `CLIENT_SECRET_OPENMETADATA` dev default). Keycloak must be up before the
  server.
- OM usernames resolve from the token email local-part (2.x default claim
  order `email, preferred_username, sub`). Do NOT set
  `AUTHENTICATION_JWT_PRINCIPAL_CLAIMS_MAPPING`: `JwtFilter` applies it to
  every non-bot token, including the OM-issued session JWT the SPA receives
  after the OIDC exchange — that internal token carries `username`/
  `preferred_username` but no mapped claim, so login appears to succeed and
  then every API call 401s (`'username' claim is not present`). With the
  default order, realm `admin` (`admin@aureliusenterprise.com`) and the OM
  session token (`admin@open-metadata.org`) both resolve to the seeded `admin`
  (admin via `AUTHORIZER_ADMIN_PRINCIPALS`), and the `openmetadata-bot`
  service-account client resolves to `ingestion-bot` through its hardcoded
  email claim. Consequence: a realm user is identified by email local-part —
  keep it aligned with the intended OM username when adding users. The
  server persists `authenticationConfiguration` in the `openmetadata_settings`
  DB table and prefers it over env on restart: after changing auth env here,
  `DELETE FROM openmetadata_settings WHERE
configtype='authenticationConfiguration'` (in the metadata Postgres) and
  recreate the server to re-seed from env.
- The ingestion loop joins `aurelius-dev-kafka-network` (broker TLS listener),
  `aurelius-dev-governance_governance-network` (server API), and
  `aurelius-dev-keycloak-network` (token endpoint by service name).
  `implicitDependencies: ["aurelius-dev-kafka"]` makes the inferred `up`/`serve`
  targets start Kafka (and its own chain: Keycloak, observability) first, and
  `ingest-openlineage` additionally `dependsOn: ["up"]` — the loop needs both
  the broker and the server stack it posts to.
- `openlineage-topic-init` (integrations compose) pre-creates the
  `openlineage-events` transport topic on the dev broker — governance owns
  the topic its pipeline consumes, not the Kafka infra. The OM OpenLineage
  connector is consumer-only (verified: its connection handler uses a
  `confluent_kafka` Consumer and no AdminClient), and its mandatory
  `CheckBrokerConnectivity` (`get_watermark_offsets` on
  partition 0) blocks in its retry loop until the partition exists. Topic
  names come from `OPENLINEAGE_TOPIC_NAMES` in `.env.enc`; created over the
  INTERNAL mTLS listener with the `openlineage-ingestion` certgen keystore —
  PKCS12, since Kafka's PEM keystore needs cert+key in one file and certgen
  issues them separately (the broker enforces `ssl.client.auth=required`).
  The app topics (`example.entity`, `example.entity-dlq`) are NOT
  provisioned here: their e2e suites create them, and producers
  auto-create-on-publish with broker defaults (3 partitions, 7d retention).
  Gotcha (verified on compose v5.6): `docker compose up --wait` treats _any_
  container exiting during the wait as a failed deployment (even exit 0), so
  a one-shot needs a `service_completed_successfully` dependant (here:
  `openlineage-ingestion`) — a dangling one-shot breaks `--wait` for the
  whole stack (this is what killed the Kafka e2e fixtures when dev/kafka
  still had a `topic-init` service).
- Scan configs elsewhere (`dev/postgres/openmetadata.yaml`,
  `dev/kafka/openmetadata.yaml`, …) are ingested by the root plugin target
  `openmetadata-ingest`, gathered here by `init-openmetadata`.
- The server runs with the **OpenTelemetry Java agent** attached and pushes
  OTLP over TLS to the dev collector: `JAVA_TOOL_OPTIONS=-javaagent:/otel/…`
  (honoured by the JVM itself, so it works regardless of the image's
  entrypoint), `OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector:4317`,
  `OTEL_EXPORTER_OTLP_CERTIFICATE=/certs/ca.pem` (one mkcert root CA
  workspace-wide already validates the collector's leaf — no extra certgen
  material), and an attach to `aurelius-dev-observability-network` — the
  same push pattern as dev/keycloak. This is the only telemetry path:
  the admin port's `/metrics` and `/metrics/prometheus` both serve
  Dropwizard JSON (verified against the running server), which Prometheus
  cannot scrape, and the app port serves the SPA at those paths.
  `OTEL_METRICS_EXPORTER=otlp` replaces its
  default Prometheus-pull endpoint (nothing scrapes :9464 here). In
  Prometheus the series carry `exported_job="openmetadata"` (the legacy
  `prometheus` exporter keeps only job/instance — same as Keycloak's);
  traces land in Tempo as `service.name=openmetadata`.
  The agent lives in the derived image rather than a host bind-mount: `up`
  stays self-contained and the jar shows up in the image SBOM (the
  docker-sbom/vuln-scan targets now cover governance too). Only the server
  service uses the derived image — `execute-migrate-all` keeps the plain
  hardened base (no JVM agent needed for migrations).
  `docker-build` is re-declared in `project.json` only to pass
  `--build-arg OM_VERSION=$(python3 tools/openmetadata/om_version.py)` —
  Nx merges the override with the inferred docker target, keeping its
  namespace/version options.
- The stack's own infrastructure (Elasticsearch, metadata Postgres) is
  monitored by the **`metrics-puller`** service — a governance-owned OTel
  Collector sidecar (`config/metrics-puller.yaml`) that scrapes both over
  TLS with the credentials already in this project and pushes OTLP to the dev
  collector, joining `observability-network` like the server does. Pull-side
  deliberately lives here, not in dev/observability: the scrape credentials
  and CA stay local to the slice, and dev/observability stays slice-agnostic
  (it receives from whoever exports). Neither speaks OTLP and neither is
  Prometheus-scrapeable for free — ES's `/_prometheus/metrics` is
  Platinum-gated (404 on this licence), while the `elasticsearchreceiver`
  reads the free `_cluster`/`_nodes` stats APIs; there is no
  `opensearchreceiver` to swap to either. Prometheus series carry
  `exported_job="openmetadata-infra"`.
- Static lineage registrations (`openlineage.yaml` in producer/connector
  projects) are gathered by `init-openlineage`, which depends on
  `init-openmetadata`: static edges reference entities created by the scans
  (apiEndpoints from the FastAPI REST scan, topics, tables), so on a fresh
  workspace the scans must run first or registration fails with
  "could not resolve …". The FastAPI REST scan in turn needs the app
  running on :8000 (`nx serve aurelius-fastapi-example`).

## What Gets Catalogued

| Service (`openmetadata.yaml` lives in)                | Connector                   | Contributes                                                                                                                                                             |
| ----------------------------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dev/postgres`                                        | `postgres`                  | databases/schemas/tables                                                                                                                                                |
| `dev/kafka`                                           | `kafka` (+ Schema Registry) | topics with Avro schemas                                                                                                                                                |
| `apps/aurelius-fastapi-example`                       | `rest`                      | apiCollections/apiEndpoints (serves https with the dev CA; scan trusts `certs/ca.pem`)                                                                                  |
| `connectors/aurelius-kafka-connect-jdbc-sink-example` | `kafkaconnect`              | connector pipelines + status (metadata only — the worker REST API exposes unresolved `${env:VAR}` config and the sink-lineage heuristic needs table-name == topic-name) |
| `dev/observability`                                   | `grafana`                   | dashboards/charts/datamodels (BETA connector; Admin service-account token in `.env.enc` as `AURELIUS_OBSERVABILITY_GRAFANA_TOKEN`)                                      |

No native scan path exists for: Schema Registry (covered via the Kafka
connector), Keycloak / kafka-ui (infrastructure), the Lambda / Node-RED /
frontend apps (no matching service type) — those stay on static edges.
Grafana panel lineage is not derivable: its queries target Prometheus/Loki/
Tempo, which have no catalog entities.

## Commands

```bash
nx up aurelius-dev-governance              # server stack (detached, healthy; Kafka chain first)
nx serve aurelius-dev-governance           # server stack (foreground; Kafka chain first)
nx ingest-openlineage aurelius-dev-governance   # OL ingestion loop (foreground; starts the stacks first)
nx init-openmetadata aurelius-dev-governance    # scan all sources once
nx init-openlineage aurelius-dev-governance     # register static lineage once
```

This project has no test suite: OpenMetadata is treated as working infra.
What we own is tested where the code lives — the producer's emitter in
`OpenLineageLifecycleTest` (Java unit tests) and the sink's native
integration in its e2e suite (asserts the events actually reach
`openlineage-events` with the right job identity). OM stitches lineage by
string equality (`"{jobNamespace}-{jobName}"` pipelines, `kafka://<host:port>`
datasets matched against the scanned `bootstrapServers`); the join
constraints each `openlineage.yaml` depends on are documented in its
comments.

> [!NOTE]
> Next step (not yet tested): the static-registration path
> (`tools/openmetadata/register.py`). In production this would be a deployed
> registration worker; the script is its early prototype and needs its own
> tests once it graduates.

UI: `http://localhost:8585` (login via Keycloak). API: same port,
`/api/v1/...`; healthcheck on admin port 8586.

## Bot authentication

Machine clients (the OL ingestion loop, the `openmetadata-ingest` /
`openlineage-register` targets) hold **no** OpenMetadata PAT. They mint a
short-lived access token from the Keycloak `openmetadata-bot`
service-account client (`client_credentials`, secret
`OIDC_BOT_CLIENT_SECRET` here / `CLIENT_SECRET_OPENMETADATA_BOT` in
`dev/keycloak`), whose hardcoded `email=ingestion-bot@open-metadata.org`
claim makes OM resolve the token to the seeded `ingestion-bot` bot user
(IngestionBotRole) via the default claims order (email, then
`preferred_username`, then `sub` — never set
`AUTHENTICATION_JWT_PRINCIPAL_CLAIMS_MAPPING`, it breaks browser login).
Keycloak signs the token with the realm keys the server already validates, so
nothing needs re-bootstrapping after `down -v` — the bot user is re-seeded
with the fresh DB.

`tools/openmetadata/kc_token.py` (stdlib-only; runs on the host and inside the
ingestion image) does the exchange and prints the `id_token`. It reads
`KEYCLOAK_BOT_TOKEN_URL` / `OIDC_BOT_CLIENT_ID` / `OIDC_BOT_CLIENT_SECRET`
from the environment, falling back to `dev/governance/.env`. The ingestion
loop calls it once per 60s cycle (a token outlives a cycle, so rotation is
free); the plugin targets run it on the host and pass the result to the
container with `docker run -e OM_JWT_TOKEN=…`.

> [!NOTE]
> Use the container-network URL (`http://keycloak:8080/...`, set in
> `integrations/docker-compose.yaml`) inside containers and the host URL
> (`keycloak.localhost:8080`, committed in `.env`) from the host —
> `keycloak.localhost` only resolves on the host.

## Conventions

- The OpenMetadata version is pinned once: `OPENMETADATA_VERSION` in
  `.env.enc`. The migration container (`docker-compose.yaml`), the derived
  server image's base (`Dockerfile`, fed by the `docker-build` target's
  `OM_VERSION` build arg), the ingestion image
  (`integrations/docker-compose.yaml`) and the `openmetadata-ingest` target
  (`tools/plugins/openmetadata.ts`, via `tools/openmetadata/om_version.py`)
  all resolve it from there — bump the env key only.
- The OpenTelemetry agent version is pinned once, in `Dockerfile`: the
  download URL and the `--checksum` SHA-256 change together (from the
  release's `checksums.txt`). Nothing else references it.
- Certificates are per-developer (`nx certgen`), never committed; scan
  configs reference them via `inline:/certs/...` markers resolved by
  `tools/openmetadata/render_inline.py` inside the ingestion container.

## Removal

Optional governance layer. Removing it means deleting this directory, the
`openmetadata-ingest` targets contributed by `tools/plugins/openmetadata.ts`,
the `openlineage-register` targets + `openlineage.yaml` files, the OL wiring in
the Java producer / sink connector, the `openmetadata-bot` client and
its hardcoded `email` claim in `dev/keycloak/import/openmetadata-realm.json`, and the
`OpenMetadata`/`OpenLineage` rows in `docs/architecture/data-governance`.
Deleting the directory also drops the derived image and its `docker-*`
targets (they are inferred from `Dockerfile`). To remove only the OTel layer:
delete `Dockerfile` and the `docker-build` target, point the server service
back at `dhi.io/openmetadata:${OPENMETADATA_VERSION:?}-debian13`, and drop
the `OTEL_*`/`JAVA_TOOL_OPTIONS` env and the `observability-network` attach
from that service — dev/observability needs no change (it receives telemetry
from whoever exports).
To remove only the infra metrics: delete the `metrics-puller` service and
`config/metrics-puller.yaml` (the `observability-network` stays — the server
pushes through it).

# aurelius-atlas-dev-observability

Local development telemetry stack (OTel Collector, Prometheus, Loki, Tempo,
Grafana). This file covers wiring specific to this project; workspace-wide
rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — the five services, all on
  `aurelius-atlas-dev-observability-network`
- `config/` — collector pipelines and Prometheus/Loki/Tempo configs.
  Histograms pushed over OTLP may aggregate exponentially (logfire,
  Keycloak/micrometer); the collector's prometheus exporter converts those
  to Prometheus native histograms, which exist only in the protobuf format
  — the `otel-collector` scrape job negotiates `PrometheusProto` with
  `scrape_native_histograms: true`, else they collapse to a lone `+Inf`
  bucket and `histogram_quantile` is permanently NaN. Query them at the
  base metric name without `by (le)`:
  `histogram_quantile(0.95, sum(rate(<metric>[5m])))`. Native form has no
  `_count`/`_sum` siblings either — count/sum panels wrap it with
  `histogram_count(rate(<metric>[5m]))` or
  `histogram_sum(rate(<metric>[5m]))`. Micrometer
  ships no buckets at all for `http_server_requests` — the Keycloak
  dashboard uses avg (`_sum`/`_count`) plus
  `http_server_requests_max_milliseconds` instead.
  The OTel **JS** SDK (browser web vitals) records with explicit buckets, so
  those histograms stay _classic_ — query `<metric>_bucket` with `sum by
(le)` as usual; and since OTel pushes are last-value (no scrape per
  interaction), the frontend dashboard reads the live cumulative `_bucket`
  instead of `rate()` to avoid NaN between ticks.
- `config/grafana/` — file-provisioned datasources and the **dashboards**
  folder: one dashboard per app/dev stack (`aurelius-atlas-fastapi`,
  `aurelius-atlas-frontend`, `aurelius-atlas-webapp`, `aurelius-atlas-keycloak`,
  `aurelius-atlas-postgres`, `aurelius-atlas-elasticsearch`,
  `aurelius-atlas-observability-stack`), all in the
  "Aurelius" folder. They are plain JSON edited in the repo (Grafana's UI
  edits are lost on recreate), keyed by the telemetry identities the slices
  export (`exported_job` / `service_name` / `service.name` = the slice's
  puller/agent name). Prometheus scrapes the stack's own components
  (collector internal :8888, loki, tempo) for the self-monitoring dashboard
  — that scrape stays _inside this compose project_, it is not scraping
  other slices.
  Panel conventions: every dashboard, row and panel carries a `description`
  (renders as the ⓘ hover hint) explaining units and what a bad value looks
  like; sparse dev-traffic counters use `increase(…[5m])` with titles like
  "… (per bucket)" (whole counts) instead of `rate()` fractional per-second
  values. The window is `[$__interval]` with a per-target `interval: 1m`
  minimum, so buckets adapt to the selected range/panel width (1-minute
  floor = 4 scrape intervals); adjacent buckets sum to the total. Keep
  `rate()` only where the quantity is inherently per-second (throughput,
  quantiles, bytes/s) or high-volume enough that fractions are meaningful.
- `scripts/init-grafana.sh` — provisions Grafana datasources on first start

## Wiring Checklist

- Targets are purely inferred from the compose file (`project.json` has none) —
  add compose-level config there, not in `project.json`.
- Everything exports to the **collector**, never directly to a backend; new
  instrumented projects follow the same pattern. Ingest is three credential-typed
  legs (DD-103, DD-107): the **browser leg** is `otlp` HTTP :4318 behind the `oidc`
  extension (Keycloak user JWTs, audience `otel-collector`; the SPAs' `/otel`
  proxies pass `Authorization` through), the **per-service leg** is `otlp/services`
  gRPC :4317 + HTTP :4319 behind the SAME `oidc` extension (client-credentials JWTs
  from the `otel-*` realm clients — the slice pullers' `oauth2client` extension,
  the Atlas server's in-app refresh shim; `azp` stamps `otel.ingest.client`), and
  the **legacy leg** is `otlp/legacy` gRPC :4320 + HTTP :4321 behind
  `bearertokenauth` (shared `OTEL_COLLECTOR_INGEST_TOKEN`, Keycloak-native OTLP +
  the FastAPI example only — producers that cannot present a Keycloak JWT). The
  contrib image has **no `compositeauth` extension**, so one port carries exactly
  one authenticator — a bearer works on exactly one leg (401 elsewhere), which is
  what makes the legs credential-typed. All receivers serve TLS only
  (`config/otel-collector.yaml` uses this
  project's `certs/`, `nx certgen`) — exporters set
  `OTEL_EXPORTER_OTLP_CERTIFICATE` (Keycloak instead needs the JVM truststore
  in `JAVA_OPTS`). The `oidc` extension is configured in its current
  `providers` shape (`issuer_url` + `issuer_ca_path` per provider; the flat
  top-level single-provider keys are deprecated) and discovers JWKS from the
  issuer URL, so
  `OTEL_COLLECTOR_OIDC_ISSUER` must match the `iss` claim the browser tokens
  carry (dev `:8080`, e2e `:8443`; the webapp e2e `conftest.py` overrides the
  env per suite) and `OTEL_COLLECTOR_OIDC_CA_FILE` (empty = no pin on the
  plaintext dev listener) points at the shared mkcert CA, mounted from
  `apps/aurelius-atlas-webapp/certs`. Discovery is a startup dependency on
  Keycloak, and the container gets `keycloak.localhost:host-gateway` since
  `:8443` is loopback-published. The per-service producers mint from the SAME
  issuer pair: the slice pullers read `OTEL_INGEST_TOKEN_URL`/`OTEL_INGEST_CA_FILE`
  (their compose defaults, the e2e conftests flip them with the collector).
- Consumers started via `nx serve`: the FastAPI example (OTLP, legacy leg :4321),
  Keycloak (`implicitDependencies` here; native OTLP on the legacy leg :4320,
  its puller on the per-service leg :4317), the Atlas server (`nx serve` chains
  dev-keycloak since DD-107 — its export mints ingest JWTs), and the frontend
  (via its `/otel` dev proxy to the browser leg at `:4318`).
- Slices that own components speaking no OTLP (databases) ship their own
  **`metrics-puller`** sidecar — a Collector that scrapes locally, next to the
  targets and credentials, and pushes OTLP here: `dev-postgres` (app PG) and
  `keycloak-infra` (Keycloak's PG). Keep this project slice-agnostic: it
  receives from whoever exports, and never scrapes other slices directly.
- Containers run as unprivileged user `65532` — keep bind-mounted config
  readable by that uid.

## Commands

```bash
nx serve aurelius-atlas-dev-observability   # Grafana on http://localhost:3000
```

> [!NOTE]
> Grafana is anonymous-Viewer only (`GF_AUTH_DISABLE_LOGIN_FORM=true`; no admin
> login exists). A browser showing "Unauthorized" while `127.0.0.1:3000` works
> has a stale `grafana_session` cookie on the `localhost` host (cookies are
> per-host, not per-port) — Grafana validates it and 401s without falling back
> to anonymous. Fix in the browser: visit `/logout` (clears the cookie) or
> delete `grafana_session` in DevTools.

## Conventions

- Add metrics/traces pipelines in `config/` and reload by restarting the
  collector service rather than editing compose env vars.
- Browser-leg pushes carry the OIDC token's `sub` as the `enduser.id`
  resource attribute (claim copy in `config/otel-collector.yaml`, DD-105);
  the metrics pipeline promotes it to the `enduser_id` Prometheus label with
  a `transform` datapoint statement — the prometheus exporter drops other
  resource attributes. The per-service leg stamps `otel.ingest.client` from
  the token's `azp` (the client id) and `transform/identity` clears
  `enduser.id` on `otel-*` pushes — machine telemetry wears no user identity
  (DD-107, CIA-09). Read traces back with `GET :3200/api/traces/<id>`
  (plural; Tempo 3.x).

## Removal

Part of the spine (workflow reference architecture). Removing it means dropping
the OTLP export wiring from the FastAPI example, Keycloak, and the frontend's
`/otel` proxy and `aurelius-atlas-observability` usage.

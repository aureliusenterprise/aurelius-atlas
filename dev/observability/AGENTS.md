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
  `aurelius-atlas-frontend`, `aurelius-atlas-keycloak`, `aurelius-atlas-postgres`,
  `aurelius-atlas-elasticsearch`,
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
- Everything exports to the **collector** (4317 gRPC / 4318 HTTP), never
  directly to a backend; new instrumented projects follow the same pattern.
  Both receivers serve TLS only (`config/otel-collector.yaml` uses this
  project's `certs/`, `nx certgen`) — exporters set `OTEL_EXPORTER_OTLP_CERTIFICATE`
  (Keycloak instead needs the JVM truststore in `JAVA_OPTS`).
- Consumers started via `nx serve`: the FastAPI example (OTLP), Keycloak
  (`implicitDependencies` here), and the frontend (via its `/otel` dev proxy to
  `:4318`).
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

## Removal

Part of the spine (workflow reference architecture). Removing it means dropping
the OTLP export wiring from the FastAPI example, Keycloak, and the frontend's
`/otel` proxy and `aurelius-atlas-observability` usage.

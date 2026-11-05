# Monitoring

Every part exports its traces and metrics over OTLP to the collector, never straight to a backend. The collector's Prometheus exporter turns the metrics into series labelled with the part's name as `exported_job`. Each part signs in to the collector with its own credential: its `otel-*` client of the realm.

## What the server sends

| Signal | Source | Keyed by |
| --- | --- | --- |
| Traces | the FastAPI instrumentation; the Elasticsearch client's spans | `service.name` = `aurelius-atlas-server` |
| Metrics | `http.server.request.duration` and `http.server.active_requests` | `http_route`, `http_request_method`, `http_response_status_code` |
| Metrics | the process and CPython groups of the system metrics | `exported_instance`, one per process |
| Logs | see [Logging](<https://aureliusenterprise.github.io/docs-roadmap-statuses/architecture/platform/observability/logging/index.md>) | `service_name` |

The HTTP metrics follow the stable semantic conventions (`OTEL_SEMCONV_STABILITY_OPT_IN=http`): their requests are labelled by route template, such as `/api/atlas/v2/entity/guid/{guid}`, never by the path itself, so a series per entity never appears.

## Dashboards

The dashboards are plain JSON in `dev/observability/config/grafana/dashboards/`, byte-copied into the chart. They sit in Grafana's "Aurelius" folder:

| Dashboard | What it shows |
| --- | --- |
| Aurelius Atlas Server | requests by status, latency and errors by route, the process, its logs and traces |
| Aurelius Atlas Webapp | the browser's web vitals and errors |
| Keycloak | the identity server, its JVM and its database |
| Elasticsearch | the store's health, shards, memory and breakers |
| Observability Stack | the collector's throughput and queues, Prometheus, Loki and Tempo themselves |

Each panel's description says its unit and what a bad value looks like. The server dashboard is where an alert from [Alerting](<https://aureliusenterprise.github.io/docs-roadmap-statuses/architecture/platform/observability/alerting/index.md>) is read first.

## Load

The server's load test runs concurrent users through reads, searches, updates and creates against the dev store, and reports each operation's percentiles. It runs with the server's e2e suite:

```
npx nx e2e aurelius-atlas-server
```

`AURELIUS_ATLAS_LOAD_USERS` (8), `AURELIUS_ATLAS_LOAD_SECONDS` (20) and `AURELIUS_ATLAS_LOAD_P95_MS` (3000) make the run longer or the budget tighter. Its first runs answer reads and searches in 30 to 120 ms, and writes in one to two seconds, the time a write waits for the store's refresh.

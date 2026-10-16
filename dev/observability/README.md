# aurelius-dev-observability

Local development observability stack: an OpenTelemetry Collector fronting
Prometheus (metrics), Loki (logs), and Tempo (traces), with Grafana as the UI.

Part of the template **spine**.

## Services

| Service        | Image         | Host port      | Purpose                         |
| -------------- | ------------- | -------------- | ------------------------------- |
| otel-collector | OpenTelemetry | 4317 / 4318    | OTLP gRPC / HTTP ingest         |
| prometheus     | Prometheus    | 9090           | Metrics (OTLP receiver)         |
| loki           | Grafana Loki  | 3100           | Log aggregation                 |
| tempo          | Grafana Tempo | 3200           | Distributed tracing             |
| grafana        | Grafana       | 127.0.0.1:3000 | Dashboards for all of the above |

All services join the `aurelius-dev-observability-network`; apps send telemetry to
the collector (`4317` gRPC, `4318` HTTP) rather than to each backend.

## Configuration

- Collector pipelines, Prometheus/Tempo/Loki configs live under `config/`
- `scripts/init-grafana.sh` provisions Grafana datasources on first start
- Containers run as the unprivileged `65532` user

## Running

```bash
nx serve aurelius-dev-observability
```

Grafana is on `http://localhost:3000`. The FastAPI example, Keycloak, the
frontend (via its `/otel` dev proxy) all export here automatically when started
through `nx serve`/`nx up`. Components that speak no OTLP (databases) arrive
via a slice-owned `metrics-puller` sidecar in postgres and keycloak. The OTLP receivers
(4317/4318) serve TLS only — exporters
trust the local CA (each project's `certs/`, `nx certgen`); the browser-facing UI ports
(Grafana, Prometheus) stay plaintext on a developer machine (ADR 039).

Dashboards are file-provisioned from `config/grafana/dashboards/` — one per
application/dev stack (FastAPI, frontend, Keycloak, Postgres, and
the observability stack itself), all in the **Aurelius** folder. Edit the
JSON in the repo rather than the UI: provisioning overwrites UI edits.

# aurelius-atlas-dev-observability

Local development observability stack: an OpenTelemetry Collector fronting
Prometheus (metrics), Loki (logs), and Tempo (traces), with Grafana as the UI.

Part of the template **spine**.

## Services

| Service        | Image         | Host port                  | Purpose                                         |
| -------------- | ------------- | -------------------------- | ----------------------------------------------- |
| otel-collector | OpenTelemetry | 4318 · 4317/4319 · 4320/21 | OTLP ingest: browser leg · per-service · legacy |
| prometheus     | Prometheus    | 9090                       | Metrics (OTLP receiver)                         |
| loki           | Grafana Loki  | 3100                       | Log aggregation                                 |
| tempo          | Grafana Tempo | 3200                       | Distributed tracing                             |
| grafana        | Grafana       | 127.0.0.1:3000             | Dashboards for all of the above                 |

All services join the `aurelius-atlas-dev-observability-network`; apps send telemetry to
the collector (`4318` for browsers, `4317` gRPC / `4319` HTTP for services with a
Keycloak identity, `4320` gRPC / `4321` HTTP for the shared-token legacy leg)
rather than to each backend.

## Configuration

- Collector pipelines, Prometheus/Tempo/Loki configs live under `config/`
- `scripts/init-grafana.sh` provisions Grafana datasources on first start
- Containers run as the unprivileged `65532` user

## Running

```bash
nx serve aurelius-atlas-dev-observability
```

Grafana is on `http://localhost:3000`. The FastAPI example, Keycloak, the
frontend (via its `/otel` dev proxy) all export here automatically when started
through `nx serve`/`nx up`. Components that speak no OTLP (databases) arrive
via a slice-owned `metrics-puller` sidecar in postgres and keycloak. The OTLP
receivers serve TLS only — exporters trust the local CA (each project's
`certs/`, `nx certgen`) — and authenticate the writer in three credential-typed
legs (DD-193, DD-196): the browser leg (4318) validates the signed-in user's
Keycloak token (OIDC, audience `otel-collector`), the per-service leg
(4317/4319) validates client-credentials JWTs from the `otel-*` realm clients
(the pullers' `oauth2client` extension, the Atlas server's refresh shim), and
the legacy leg (4320/4321) demands the shared ingest token
(`OTEL_COLLECTOR_INGEST_TOKEN`, this project's `.env.enc`) for the producers
that cannot present a Keycloak JWT (Keycloak's native OTLP, the FastAPI
example). A bearer works on exactly one leg. The verified writer is stamped on
the telemetry (`enduser.id` from `sub`, `otel.ingest.client` from `azp`,
DD-194/DD-196). The browser-facing UI ports (Grafana, Prometheus) stay
plaintext on a developer machine (ADR 039).

Dashboards are file-provisioned from `config/grafana/dashboards/` — one per
application/dev stack (FastAPI, frontend, webapp, Keycloak, Postgres, and
the observability stack itself), all in the **Aurelius** folder. Edit the
JSON in the repo rather than the UI: provisioning overwrites UI edits.
When copying a dashboard as a template, give the copy its own `uid`/`title` and
shift the panel ids (the Grafana API file provider keys objects on the
dashboard's internal id, and a clone reusing the original's ids fails to save).

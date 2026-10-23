# aurelius-atlas-otel

The OTLP ingest credential for the collector's per-service leg (7.18, DD-107,
CIA-07), shared by every Aurelius Atlas service that exports telemetry with a
Keycloak client-credentials identity: the Atlas server and the auxiliary APIs.

The collector's per-service leg (4317 gRPC / 4319 HTTP) accepts only
client-credentials JWTs minted for the service's `otel-<service>` realm client
(audience `otel-collector`, the `otel-ingest` scope). The OTel Python SDK reads
`OTEL_EXPORTER_OTLP_HEADERS` statically, and the dev realm's access token lives
60s — a bearer JWT in a static header expires a minute in. So each app owns the
OTLP export: a refresh-ahead token source feeds a `requests.Session` that
injects a fresh bearer header on every OTLP request, handed to app-built
exporters wired into logfire through its `additional_span_processors` /
`MetricsOptions.additional_readers` seams.

## Use

```python
from aurelius_atlas_otel import ClientCredentialsTokenSource, build_otlp_pipeline

pipeline = build_otlp_pipeline(
    endpoint="https://localhost:4319",
    ca_file="certs/ca.pem",
    token_source=ClientCredentialsTokenSource(
        token_url="https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token",
        client_id="otel-aurelius-atlas-server",
        client_secret=secret,
        ca_file="certs/ca.pem",
    ),
)  # (span processor, metric reader) for logfire's seams — None-side is the app's call
```

Settings arrive as parameters: the library reads no env vars (workspace rule);
each app owns configuration via pydantic-settings. No new dependency: the
session rides the `requests` the OTLP exporter already uses, and the mint is
stdlib urllib.

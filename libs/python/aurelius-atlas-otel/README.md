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
exporters whose processor/reader `setup_telemetry` installs on the process's
native OTel providers (DD-121).

## Use

```python
from aurelius_atlas_otel import ClientCredentialsTokenSource, build_otlp_pipeline, setup_telemetry

pipeline = build_otlp_pipeline(
    endpoint="https://localhost:4319",
    ca_file="certs/ca.pem",
    token_source=ClientCredentialsTokenSource(
        token_url="https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token",
        client_id="otel-aurelius-atlas-server",
        client_secret=secret,
        ca_file="certs/ca.pem",
    ),
)
setup_telemetry("my-service", "1.0", pipeline=pipeline)  # None pipeline = no OTLP leg
```

Settings arrive as parameters: the library reads no app settings from the
environment (workspace rule) — each app owns configuration via
pydantic-settings. The one read is the standard `OTEL_EXPORTER_OTLP_ENDPOINT`
switch that turns on the env leg (DD-121, CIA-10): a third-party-runtime name,
bare by the workspace's env-prefix rule. `setup_telemetry` also registers the
per-process/CPython system instruments on the meter provider (DD-121), so
every app exports CPU/memory/GC series beside its request metrics; the
host-wide `system.*` group stays off (the dev/e2e apps share one host). No new
dependency: the session rides the `requests` the OTLP exporter already uses,
and the mint is stdlib urllib.

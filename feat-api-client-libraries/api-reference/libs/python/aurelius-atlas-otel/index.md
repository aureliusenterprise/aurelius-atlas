# aurelius-atlas-otel

The OTLP ingest credential for the collector's per-service leg (7.18, DD-107), shared by every Aurelius Atlas service that exports telemetry with a Keycloak client-credentials identity (8.0, DD-108).

## Installation

```
[project.dependencies]
aurelius-atlas-otel = "*"

[tool.uv.sources.aurelius-atlas-otel]
workspace = true
```

## Documentation

## aurelius\_atlas\_otel.ingest

The OTLP ingest credential for the collector's per-service leg (7.18, DD-107, CIA-07).

The collector's per-service leg (4317 gRPC / 4319 HTTP) accepts only Keycloak client-credentials JWTs minted for the service's realm client `otel-<service>` (audience `otel-collector`, the `otel-ingest` scope). The OTel Python SDK reads `OTEL_EXPORTER_OTLP_HEADERS` statically, and the dev realm's access token lives 60s — a bearer JWT in a static header expires a minute in. So the app owns the OTLP export: a refresh-ahead token source feeds a `requests.Session` that injects a fresh bearer header on every OTLP request, handed to app-built exporters whose processor/reader `setup_telemetry` installs on the process's providers (DD-121).

Extracted from the Atlas server's `otel_ingest` module so every service on the leg shares one credential (8.0, DD-108); the server keeps the settings mapping, this library owns the mechanism.

No new dependency: the session rides the `requests` the OTLP exporter already uses, and the mint is stdlib urllib. The dev realm's 60s token is why the header is read per request, not once.

Classes:

- **`ClientCredentialsTokenSource`** –

  Mints and caches a client-credentials JWT, refreshed ahead of expiry.

Functions:

- **`build_otlp_pipeline`** –

  The app-owned OTLP export (DD-107): a trace processor + metric reader.

Attributes:

- **`IngestPipeline`** –

  The (span processor, metric reader) pair `build_otlp_pipeline` returns,
- **`REFRESH_AHEAD_SECONDS`** –

  Refresh when the token expires within this window (the dev realm's token

### IngestPipeline

```
IngestPipeline = tuple[BatchSpanProcessor, PeriodicExportingMetricReader]
```

The (span processor, metric reader) pair `build_otlp_pipeline` returns, for `setup_telemetry`'s `span_processors` / `metric_readers`.

### REFRESH\_AHEAD\_SECONDS

```
REFRESH_AHEAD_SECONDS = 20
```

Refresh when the token expires within this window (the dev realm's token lives 60s, so a 20s margin keeps every export inside validity).

### ClientCredentialsTokenSource

```
ClientCredentialsTokenSource(token_url: str, client_id: str, client_secret: str, ca_file: str | None = None)
```

Mints and caches a client-credentials JWT, refreshed ahead of expiry.

:param token\_url: the issuer's `.../protocol/openid-connect/token` endpoint :param client\_id: the ingest client (`otel-atlas-server`) :param client\_secret: the client's secret :param ca\_file: PEM CA verifying the token endpoint's TLS (None: system trust — the dev plaintext :8080 issuer)

Methods:

- **`bearer`** –

  A valid bearer token, minting/refreshing as needed.

#### bearer

```
bearer() -> str | None
```

A valid bearer token, minting/refreshing as needed.

On mint failure with no usable token, `None` — the request then goes out header-less and the collector's 401 is the visible failure (DD-107: no silent fallback).

### build\_otlp\_pipeline

```
build_otlp_pipeline(endpoint: str, ca_file: str | None, token_source: ClientCredentialsTokenSource) -> IngestPipeline
```

The app-owned OTLP export (DD-107): a trace processor + metric reader.

The exporters inject the bearer header per export through the ingest session.

:param endpoint: the collector's service-leg base (`https://host:4319`) :param ca\_file: PEM CA verifying the collector's TLS :param token\_source: the ingest credential source :returns: a span processor and a metric reader for `setup_telemetry`

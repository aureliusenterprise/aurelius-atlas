# aurelius-atlas-otel

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-otel)

The OTLP ingest credential for the collector's per-service leg (7.18, DD-196),
shared by every Aurelius Atlas service that exports telemetry with a Keycloak
client-credentials identity (8.0, DD-197).

## Installation

```toml
[project.dependencies]
aurelius-atlas-otel = "*"

[tool.uv.sources.aurelius-atlas-otel]
workspace = true
```

## Documentation

::: aurelius_atlas_otel.ingest

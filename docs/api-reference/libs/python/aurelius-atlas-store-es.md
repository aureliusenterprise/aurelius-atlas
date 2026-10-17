# aurelius-atlas-store-es

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-store-es)

Elasticsearch access for Aurelius Atlas: settings, client lifecycle, version check and health check.

## Installation

```toml
dependencies = ["aurelius-atlas-store-es"]

[tool.uv.sources.aurelius-atlas-store-es]
workspace = true
```

Tests that need a server add `aurelius-atlas-store-es[testing]` to their dev dependencies.

## Documentation

::: aurelius_atlas_store_es

::: aurelius_atlas_store_es.testing.fake

::: aurelius_atlas_store_es.testing.container

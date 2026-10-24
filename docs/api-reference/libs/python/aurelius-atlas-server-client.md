# aurelius-atlas-server-client

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-server-client)

The contract and the async client of the Atlas REST API (8.4, DD-114, DD-115):
the admin, types and lineage models every consumer of `aurelius-atlas-server`
speaks, and the `httpx2`-based `AtlasClient` that calls it. The lineage-model app
imports the lineage wire models from here — one source of truth for both sides
of the wire.

## Installation

```toml
[project.dependencies]
aurelius-atlas-server-client = "*"

[tool.uv.sources.aurelius-atlas-server-client]
workspace = true
```

## Documentation

::: aurelius_atlas_server_client.models

::: aurelius_atlas_server_client.lineage

::: aurelius_atlas_server_client.client

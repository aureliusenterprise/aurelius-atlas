# aurelius-atlas-lineage-model-client

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-lineage-model-client)

The contract and the async client of the lineage-model API (8.4, DD-114,
DD-115): the query-parameter model of `GET /v2/lineage` and the model-document
response. The `aurelius-atlas-lineage-model` app imports its own contract from
here; a no-lineage answer (204) is `None`.

## Installation

```toml
[project.dependencies]
aurelius-atlas-lineage-model-client = "*"

[tool.uv.sources.aurelius-atlas-lineage-model-client]
workspace = true
```

## Documentation

::: aurelius_atlas_lineage_model_client.models

::: aurelius_atlas_lineage_model_client.client

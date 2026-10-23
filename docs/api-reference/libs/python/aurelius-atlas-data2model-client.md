# aurelius-atlas-data2model-client

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-data2model-client)

The contract and the async client of the data2model extraction API (8.4,
DD-114, DD-115): the rules family the legacy chain evolved (AURELIUS-RULES), the
extraction request/response, and the `Data2ModelClient` that posts them. The
`aurelius-atlas-data2model` app imports its own contract from here.

## Installation

```toml
[project.dependencies]
aurelius-atlas-data2model-client = "*"

[tool.uv.sources.aurelius-atlas-data2model-client]
workspace = true
```

## Documentation

::: aurelius_atlas_data2model_client.models

::: aurelius_atlas_data2model_client.types

::: aurelius_atlas_data2model_client.client

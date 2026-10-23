# aurelius-atlas-validate-entity-client

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-validate-entity-client)

The contract and the async client of the validate-entity API (8.4, DD-114,
DD-115): the governance validation card the screen renders and the
`ValidateEntityClient` that asks for it. The `aurelius-atlas-validate-entity`
app imports its own response model from here.

## Installation

```toml
[project.dependencies]
aurelius-atlas-validate-entity-client = "*"

[tool.uv.sources.aurelius-atlas-validate-entity-client]
workspace = true
```

## Documentation

::: aurelius_atlas_validate_entity_client.models

::: aurelius_atlas_validate_entity_client.client

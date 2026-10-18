# aurelius-atlas-model

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-model)

Atlas data shapes for Aurelius Atlas, without I/O
([DD-002](../../../architecture/conversion/design-log.md#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)).
Since increment [1.1](../../../architecture/conversion/increments/1-1-typedef-models.md): the Apache
Atlas 2.4.0 type definitions (enum, struct, classification, entity, relationship and business metadata),
their header and `AtlasTypesDef`, as Pydantic models that read and write Atlas's REST JSON. Since
[1.5](../../../architecture/conversion/increments/1-5-builtin-models.md): the patch record `AtlasPatch`.

```python
from aurelius_atlas_model.typedef import AtlasTypesDef

types = AtlasTypesDef.model_validate(request_body)  # Atlas's normalisations apply
response_body = types.to_json()  # Java names, nulls left out, epoch-millisecond dates
```

## Installation

```toml
dependencies = ["aurelius-atlas-model"]

[tool.uv.sources.aurelius-atlas-model]
workspace = true
```

## Documentation

::: aurelius_atlas_model.typedef

::: aurelius_atlas_model.patches

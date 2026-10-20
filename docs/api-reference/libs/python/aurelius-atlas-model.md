# aurelius-atlas-model

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-model)

Atlas data shapes for Aurelius Atlas, without I/O
([DD-002](../../../architecture/conversion/design-log.md#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)).
Since increment [1.1](../../../architecture/conversion/increments/1-1-typedef-models.md): the Apache
Atlas 2.4.0 type definitions (enum, struct, classification, entity, relationship and business metadata),
their header and `AtlasTypesDef`, as Pydantic models that read and write Atlas's REST JSON. Since
[1.5](../../../architecture/conversion/increments/1-5-builtin-models.md): the patch record `AtlasPatch`.
Since [2.1a](../../../architecture/conversion/increments/2-1-entity-models.md): the entity models of
`aurelius_atlas_model.instance`, one module per Atlas class (`AtlasEntity`, `AtlasEntityWithExtInfo`,
`AtlasEntityHeader`, `AtlasClassification`, `AtlasObjectId`, `EntityMutationResponse`, …), and the JSON
conventions all models share in `aurelius_atlas_model.base`.

```python
from aurelius_atlas_model.typedef import AtlasTypesDef

types = AtlasTypesDef.model_validate(request_body)  # Atlas's normalisations apply
response_body = types.to_json()  # Java names, nulls left out, epoch-millisecond dates

from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo

entities = AtlasEntitiesWithExtInfo.model_validate(request_body)  # entities without a GUID get "-<n>"
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

::: aurelius_atlas_model.base

::: aurelius_atlas_model.instance.struct

::: aurelius_atlas_model.instance.entity

::: aurelius_atlas_model.instance.entity_status

::: aurelius_atlas_model.instance.entity_ext_info

::: aurelius_atlas_model.instance.entity_with_ext_info

::: aurelius_atlas_model.instance.entities_with_ext_info

::: aurelius_atlas_model.instance.object_id

::: aurelius_atlas_model.instance.related_object_id

::: aurelius_atlas_model.instance.relationship_status

::: aurelius_atlas_model.instance.classification

::: aurelius_atlas_model.instance.time_boundary

::: aurelius_atlas_model.instance.entity_header

::: aurelius_atlas_model.instance.entity_headers

::: aurelius_atlas_model.instance.entity_operation

::: aurelius_atlas_model.instance.entity_mutation_response

::: aurelius_atlas_model.instance.term_assignment_header

::: aurelius_atlas_model.instance.term_assignment_status

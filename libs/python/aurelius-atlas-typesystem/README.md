# aurelius-atlas-typesystem

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-typesystem)

The Atlas type system for Aurelius Atlas, without I/O
([DD-002](../../../docs/architecture/conversion/design-log.md#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)):
the type registry and the types that type definitions resolve to. Since increment
[1.2](../../../docs/architecture/conversion/increments/1-2-type-registry.md): the built-in, array, map, enum
and struct types, attribute types and constraints. Since [1.3](../../../docs/architecture/conversion/increments/1-3-type-hierarchies.md):
entity and classification hierarchies, relationship and business metadata types.

```python
from aurelius_atlas_typesystem.registry import TypeRegistry

registry = TypeRegistry()
with registry.update() as transient:  # committed when the block ends, discarded when it raises
    transient.add_types(types_def)  # resolves every type; raises AtlasError on a bad reference
registry.entity_type("hive_table")
```

## Installation

```toml
dependencies = ["aurelius-atlas-typesystem"]

[tool.uv.sources.aurelius-atlas-typesystem]
workspace = true
```

## Documentation

::: aurelius_atlas_typesystem.registry

::: aurelius_atlas_typesystem.types

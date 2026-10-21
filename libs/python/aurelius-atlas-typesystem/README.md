# aurelius-atlas-typesystem

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-typesystem)

The Atlas type system for Aurelius Atlas, without I/O
([DD-002](../../../docs/architecture/conversion/design-log.md#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)):
the type registry and the types that type definitions resolve to. Since increment
[1.2](../../../docs/architecture/conversion/increments/1-2-type-registry.md): the built-in, array, map, enum
and struct types, attribute types and constraints. Since [1.3](../../../docs/architecture/conversion/increments/1-3-type-hierarchies.md):
entity and classification hierarchies, relationship and business metadata types. Since
[2.1b](../../../docs/architecture/conversion/increments/2-1-value-types.md): the value side of the built-in,
enum, array and map types, as Atlas checks, normalises and compares attribute values. Since
[2.1c](../../../docs/architecture/conversion/increments/2-1-entity-validation.md): the same for structs,
classifications (with their validity periods) and entities (with their relationship attributes).

```python
from aurelius_atlas_typesystem.registry import TypeRegistry

registry = TypeRegistry()
with registry.update() as transient:  # committed when the block ends, discarded when it raises
    transient.add_types(types_def)  # resolves every type; raises AtlasError on a bad reference
registry.entity_type("hive_table")

int_type = registry.get_type("int")
int_type.get_normalized_value("42")  # 42; Java's Integer.valueOf rules, None when invalid
registry.get_type("array<int>").validate_value(["x"], "a", messages := [])  # messages: a[0]=x: invalid value…
registry.entity_type("hive_table").validate_value(entity, "entity", messages)  # e.g. mandatory attribute missing
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

::: aurelius_atlas_typesystem.atlas_type

::: aurelius_atlas_typesystem.struct_type

::: aurelius_atlas_typesystem.classification_type

::: aurelius_atlas_typesystem.entity_type

::: aurelius_atlas_typesystem.relationship_type

::: aurelius_atlas_typesystem.business_metadata_type

::: aurelius_atlas_typesystem.attribute

::: aurelius_atlas_typesystem.enum_type

::: aurelius_atlas_typesystem.array_type

::: aurelius_atlas_typesystem.map_type

::: aurelius_atlas_typesystem.builtin

::: aurelius_atlas_typesystem.java

# aurelius-atlas-typesystem

The Atlas type system for Aurelius Atlas, without I/O ([DD-002](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)): the type registry and the types that type definitions resolve to. Since increment [1.2](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/conversion/increments/1-2-type-registry/index.md>): the built-in, array, map, enum and struct types, attribute types and constraints. Since [1.3](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/conversion/increments/1-3-type-hierarchies/index.md>): entity and classification hierarchies, relationship and business metadata types. Since [2.1b](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/conversion/increments/2-1-value-types/index.md>): the value side of the built-in, enum, array and map types, as Atlas checks, normalises and compares attribute values. Since [2.1c](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/conversion/increments/2-1-entity-validation/index.md>): the same for structs, classifications (with their validity periods) and entities (with their relationship attributes).

```
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

```
dependencies = ["aurelius-atlas-typesystem"]

[tool.uv.sources.aurelius-atlas-typesystem]
workspace = true
```

## Documentation

## aurelius\_atlas\_typesystem.registry

The type registry and its transient copy (`AtlasTypeRegistry`, TRG-01 to TRG-09, DD-024).

Readers use a `TypeRegistry`. Writers take a `TransientTypeRegistry` from `lock_for_update`, change it, and release it with or without committing; until the commit, readers see the registry as it was.

Classes:

- **`TransientTypeRegistry`** –

  A copy of a registry that changes and resolves before it is committed (`AtlasTransientTypeRegistry`).
- **`TypeRegistry`** –

  The resolved types of the server (`AtlasTypeRegistry`).

Attributes:

- **`DEFAULT_LOCK_TIMEOUT_SECONDS`** –

  Atlas's `atlas.server.type.update.lock.max.wait.time.seconds` default.

### DEFAULT\_LOCK\_TIMEOUT\_SECONDS

```
DEFAULT_LOCK_TIMEOUT_SECONDS = 15.0
```

Atlas's `atlas.server.type.update.lock.max.wait.time.seconds` default.

### TransientTypeRegistry

```
TransientTypeRegistry()
```

Bases: `TypeRegistry`

A copy of a registry that changes and resolves before it is committed (`AtlasTransientTypeRegistry`).

Methods:

- **`add_type`** –

  Add a definition, then resolve every type (TRG-06, TRG-09).
- **`add_types`** –

  Add definitions, then resolve every type (TRG-06, TRG-09).
- **`all_service_types`** –

  The service types of every registered type (TRG-04).
- **`all_type_names`** –

  Every registered type name, built-in ones included (TRG-04).
- **`all_types`** –

  Every registered type (TRG-04).
- **`business_metadata_type`** –

  The business metadata type named `name`, or None (TRG-04).
- **`classification_type`** –

  The classification type named `name`, or None (TRG-04).
- **`clear`** –

  Drop every definition, keeping the built-in types (`AtlasTransientTypeRegistry.clear`).
- **`copy_of`** –

  A copy holding the registry's definitions as new, unresolved types (TRG-05).
- **`entity_type`** –

  The entity type named `name`, or None (TRG-04).
- **`enum_type`** –

  The enum type named `name`, or None (TRG-04).
- **`get_type`** –

  The type named `type_name`, building `array<T>` and `map<K,V>` types on demand (TRG-02, TRG-03).
- **`get_type_by_guid`** –

  The type whose definition has `guid` (TRG-03).
- **`is_registered`** –

  Whether `type_name` is a registered type; built array and map names are not (TRG-04).
- **`lock_for_update`** –

  Take the update lock and a transient copy of this registry to change (TRG-05).
- **`relationship_type`** –

  The relationship type named `name`, or None (TRG-04).
- **`release`** –

  Release the update lock; on the last release, make the copy's types the registry's when `commit`.
- **`remove_type_by_guid`** –

  Remove the definition with `guid`, then resolve (TRG-08, TRG-09).
- **`remove_type_by_name`** –

  Remove the definition named `name`, then resolve (TRG-08, TRG-09).
- **`remove_types`** –

  Remove each definition by its GUID when it has one, else by its name, then resolve (TRG-08, TRG-09).
- **`struct_type`** –

  The struct type named `name`, or None (TRG-04).
- **`typedef_by_guid`** –

  The definition with `guid`, of any kind (TRG-04).
- **`typedef_by_name`** –

  The definition named `name`, of any kind (TRG-04).
- **`typedef_names`** –

  The names of the definitions of one kind (TRG-04).
- **`typedefs`** –

  The definitions of one kind, such as every `ENTITY` definition (TRG-04).
- **`types`** –

  The types of one kind (TRG-04).
- **`update`** –

  Change the registry: commit when the block ends normally, discard when it raises (TRG-05, TRG-09).
- **`update_type`** –

  Replace the definition with `typedef`'s GUID, else its name, then resolve (TRG-07, TRG-09).
- **`update_type_by_guid`** –

  Replace the definition with `guid` by `typedef`, then resolve (TRG-07, TRG-09).
- **`update_type_by_name`** –

  Replace the definition named `name` by `typedef`, then resolve (TRG-07, TRG-09).
- **`update_types`** –

  Replace each definition by GUID, else by name, then resolve (TRG-07, TRG-09).
- **`update_types_without_resolving`** –

  Replace each definition by GUID, else by name, and leave resolving to the next change (MDL-03).

Attributes:

- **`added`** (`list[AtlasBaseTypeDef]`) –
- **`deleted`** (`list[AtlasBaseTypeDef]`) –
- **`updated`** (`list[AtlasBaseTypeDef]`) –

#### added

```
added: list[AtlasBaseTypeDef] = []
```

#### deleted

```
deleted: list[AtlasBaseTypeDef] = []
```

#### updated

```
updated: list[AtlasBaseTypeDef] = []
```

#### add\_type

```
add_type(typedef: AtlasBaseTypeDef | None) -> None
```

Add a definition, then resolve every type (TRG-06, TRG-09).

#### add\_types

```
add_types(typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> None
```

Add definitions, then resolve every type (TRG-06, TRG-09).

#### all\_service\_types

```
all_service_types() -> set[str]
```

The service types of every registered type (TRG-04).

#### all\_type\_names

```
all_type_names() -> list[str]
```

Every registered type name, built-in ones included (TRG-04).

#### all\_types

```
all_types() -> list[AtlasType]
```

Every registered type (TRG-04).

#### business\_metadata\_type

```
business_metadata_type(name: str | None) -> BusinessMetadataType | None
```

The business metadata type named `name`, or None (TRG-04).

#### classification\_type

```
classification_type(name: str | None) -> ClassificationType | None
```

The classification type named `name`, or None (TRG-04).

#### clear

```
clear() -> None
```

Drop every definition, keeping the built-in types (`AtlasTransientTypeRegistry.clear`).

#### copy\_of

```
copy_of(registry: TypeRegistry) -> Self
```

A copy holding the registry's definitions as new, unresolved types (TRG-05).

#### entity\_type

```
entity_type(name: str | None) -> EntityType | None
```

The entity type named `name`, or None (TRG-04).

#### enum\_type

```
enum_type(name: str | None) -> EnumType | None
```

The enum type named `name`, or None (TRG-04).

#### get\_type

```
get_type(type_name: str | None) -> AtlasType
```

The type named `type_name`, building `array<T>` and `map<K,V>` types on demand (TRG-02, TRG-03).

Raises:

- `AtlasError` –

  `TYPE_NAME_NOT_FOUND` when the name, or an element, key or value name, is unknown.

#### get\_type\_by\_guid

```
get_type_by_guid(guid: str | None) -> AtlasType
```

The type whose definition has `guid` (TRG-03).

Raises:

- `AtlasError` –

  `TYPE_GUID_NOT_FOUND` when no definition has it.

#### is\_registered

```
is_registered(type_name: str | None) -> bool
```

Whether `type_name` is a registered type; built array and map names are not (TRG-04).

#### lock\_for\_update

```
lock_for_update(timeout: float | None = None) -> TransientTypeRegistry
```

Take the update lock and a transient copy of this registry to change (TRG-05).

The lock is re-entrant: a thread that holds it gets the same copy again.

Raises:

- `AtlasError` –

  `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` when the lock is not free within the timeout.

#### relationship\_type

```
relationship_type(name: str | None) -> RelationshipType | None
```

The relationship type named `name`, or None (TRG-04).

#### release

```
release(transient: TransientTypeRegistry, *, commit: bool) -> None
```

Release the update lock; on the last release, make the copy's types the registry's when `commit`.

A copy that is not the one handed out is not committed (TRG-05).

#### remove\_type\_by\_guid

```
remove_type_by_guid(guid: str | None) -> None
```

Remove the definition with `guid`, then resolve (TRG-08, TRG-09).

#### remove\_type\_by\_name

```
remove_type_by_name(name: str | None) -> None
```

Remove the definition named `name`, then resolve (TRG-08, TRG-09).

#### remove\_types

```
remove_types(types_def: AtlasTypesDef | None) -> None
```

Remove each definition by its GUID when it has one, else by its name, then resolve (TRG-08, TRG-09).

#### struct\_type

```
struct_type(name: str | None) -> StructType | None
```

The struct type named `name`, or None (TRG-04).

#### typedef\_by\_guid

```
typedef_by_guid(guid: str | None) -> AtlasBaseTypeDef | None
```

The definition with `guid`, of any kind (TRG-04).

#### typedef\_by\_name

```
typedef_by_name(name: str | None) -> AtlasBaseTypeDef | None
```

The definition named `name`, of any kind (TRG-04).

#### typedef\_names

```
typedef_names(kind: TypeCategory) -> list[str]
```

The names of the definitions of one kind (TRG-04).

#### typedefs

```
typedefs(kind: TypeCategory) -> list[AtlasBaseTypeDef]
```

The definitions of one kind, such as every `ENTITY` definition (TRG-04).

#### types

```
types(kind: TypeCategory) -> list[AtlasType]
```

The types of one kind (TRG-04).

#### update

```
update(timeout: float | None = None) -> Iterator[TransientTypeRegistry]
```

Change the registry: commit when the block ends normally, discard when it raises (TRG-05, TRG-09).

#### update\_type

```
update_type(typedef: AtlasBaseTypeDef | None) -> None
```

Replace the definition with `typedef`'s GUID, else its name, then resolve (TRG-07, TRG-09).

#### update\_type\_by\_guid

```
update_type_by_guid(guid: str | None, typedef: AtlasBaseTypeDef | None) -> None
```

Replace the definition with `guid` by `typedef`, then resolve (TRG-07, TRG-09).

#### update\_type\_by\_name

```
update_type_by_name(name: str | None, typedef: AtlasBaseTypeDef | None) -> None
```

Replace the definition named `name` by `typedef`, then resolve (TRG-07, TRG-09).

#### update\_types

```
update_types(typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> None
```

Replace each definition by GUID, else by name, then resolve (TRG-07, TRG-09).

#### update\_types\_without\_resolving

```
update_types_without_resolving(typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> None
```

Replace each definition by GUID, else by name, and leave resolving to the next change (MDL-03).

`updateTypesWithNoRefResolve`: `createUpdateTypesDef` replaces the updated definitions first, so that the definitions it then creates resolve against them.

### TypeRegistry

```
TypeRegistry(lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS)
```

The resolved types of the server (`AtlasTypeRegistry`).

Methods:

- **`all_service_types`** –

  The service types of every registered type (TRG-04).
- **`all_type_names`** –

  Every registered type name, built-in ones included (TRG-04).
- **`all_types`** –

  Every registered type (TRG-04).
- **`business_metadata_type`** –

  The business metadata type named `name`, or None (TRG-04).
- **`classification_type`** –

  The classification type named `name`, or None (TRG-04).
- **`entity_type`** –

  The entity type named `name`, or None (TRG-04).
- **`enum_type`** –

  The enum type named `name`, or None (TRG-04).
- **`get_type`** –

  The type named `type_name`, building `array<T>` and `map<K,V>` types on demand (TRG-02, TRG-03).
- **`get_type_by_guid`** –

  The type whose definition has `guid` (TRG-03).
- **`is_registered`** –

  Whether `type_name` is a registered type; built array and map names are not (TRG-04).
- **`lock_for_update`** –

  Take the update lock and a transient copy of this registry to change (TRG-05).
- **`relationship_type`** –

  The relationship type named `name`, or None (TRG-04).
- **`release`** –

  Release the update lock; on the last release, make the copy's types the registry's when `commit`.
- **`struct_type`** –

  The struct type named `name`, or None (TRG-04).
- **`typedef_by_guid`** –

  The definition with `guid`, of any kind (TRG-04).
- **`typedef_by_name`** –

  The definition named `name`, of any kind (TRG-04).
- **`typedef_names`** –

  The names of the definitions of one kind (TRG-04).
- **`typedefs`** –

  The definitions of one kind, such as every `ENTITY` definition (TRG-04).
- **`types`** –

  The types of one kind (TRG-04).
- **`update`** –

  Change the registry: commit when the block ends normally, discard when it raises (TRG-05, TRG-09).

#### all\_service\_types

```
all_service_types() -> set[str]
```

The service types of every registered type (TRG-04).

#### all\_type\_names

```
all_type_names() -> list[str]
```

Every registered type name, built-in ones included (TRG-04).

#### all\_types

```
all_types() -> list[AtlasType]
```

Every registered type (TRG-04).

#### business\_metadata\_type

```
business_metadata_type(name: str | None) -> BusinessMetadataType | None
```

The business metadata type named `name`, or None (TRG-04).

#### classification\_type

```
classification_type(name: str | None) -> ClassificationType | None
```

The classification type named `name`, or None (TRG-04).

#### entity\_type

```
entity_type(name: str | None) -> EntityType | None
```

The entity type named `name`, or None (TRG-04).

#### enum\_type

```
enum_type(name: str | None) -> EnumType | None
```

The enum type named `name`, or None (TRG-04).

#### get\_type

```
get_type(type_name: str | None) -> AtlasType
```

The type named `type_name`, building `array<T>` and `map<K,V>` types on demand (TRG-02, TRG-03).

Raises:

- `AtlasError` –

  `TYPE_NAME_NOT_FOUND` when the name, or an element, key or value name, is unknown.

#### get\_type\_by\_guid

```
get_type_by_guid(guid: str | None) -> AtlasType
```

The type whose definition has `guid` (TRG-03).

Raises:

- `AtlasError` –

  `TYPE_GUID_NOT_FOUND` when no definition has it.

#### is\_registered

```
is_registered(type_name: str | None) -> bool
```

Whether `type_name` is a registered type; built array and map names are not (TRG-04).

#### lock\_for\_update

```
lock_for_update(timeout: float | None = None) -> TransientTypeRegistry
```

Take the update lock and a transient copy of this registry to change (TRG-05).

The lock is re-entrant: a thread that holds it gets the same copy again.

Raises:

- `AtlasError` –

  `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` when the lock is not free within the timeout.

#### relationship\_type

```
relationship_type(name: str | None) -> RelationshipType | None
```

The relationship type named `name`, or None (TRG-04).

#### release

```
release(transient: TransientTypeRegistry, *, commit: bool) -> None
```

Release the update lock; on the last release, make the copy's types the registry's when `commit`.

A copy that is not the one handed out is not committed (TRG-05).

#### struct\_type

```
struct_type(name: str | None) -> StructType | None
```

The struct type named `name`, or None (TRG-04).

#### typedef\_by\_guid

```
typedef_by_guid(guid: str | None) -> AtlasBaseTypeDef | None
```

The definition with `guid`, of any kind (TRG-04).

#### typedef\_by\_name

```
typedef_by_name(name: str | None) -> AtlasBaseTypeDef | None
```

The definition named `name`, of any kind (TRG-04).

#### typedef\_names

```
typedef_names(kind: TypeCategory) -> list[str]
```

The names of the definitions of one kind (TRG-04).

#### typedefs

```
typedefs(kind: TypeCategory) -> list[AtlasBaseTypeDef]
```

The definitions of one kind, such as every `ENTITY` definition (TRG-04).

#### types

```
types(kind: TypeCategory) -> list[AtlasType]
```

The types of one kind (TRG-04).

#### update

```
update(timeout: float | None = None) -> Iterator[TransientTypeRegistry]
```

Change the registry: commit when the block ends normally, discard when it raises (TRG-05, TRG-09).

## aurelius\_atlas\_typesystem.types

Atlas types: the classes a type definition resolves to, one module per Java class (DD-025, DD-041).

This module re-exports them and makes the unresolved type of a definition (`type_of`).

Classes:

- **`ArrayType`** –

  `array<T>` with its cardinality and value counts (`AtlasArrayType`, TRG-02).
- **`AtlasAttribute`** –

  A resolved attribute of a struct-like type (`AtlasStructType.AtlasAttribute`).
- **`AtlasType`** –

  A type: its name, category and service type, and how it checks, normalises and compares values.
- **`BuiltInType`** –

  A primitive type such as `string` or `int`, of the `atlas_core` service type (TRG-01).
- **`BusinessAttribute`** –

  A business metadata attribute and the entity types it applies to (`AtlasBusinessAttribute`, THY-12).
- **`BusinessMetadataType`** –

  A business metadata type: its attributes and the entity types they apply to (THY-12).
- **`ClassificationType`** –

  A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07).
- **`EdgeDirection`** –

  Which way a relationship attribute's edge points (`AtlasRelationshipEdgeDirection`, THY-10).
- **`EntityType`** –

  An entity type: its hierarchy, relationship and business attributes (THY-01 to THY-06, THY-10 to THY-12).
- **`EnumType`** –

  An enum type: its elements by value and ordinal, and its default (`AtlasEnumType`, TRG-14).
- **`MapType`** –

  `map<K,V>` (`AtlasMapType`, TRG-02).
- **`ObjectIdType`** –

  `objectid`: a reference to an entity of `object_type`, by GUID or by unique attributes.
- **`RelationshipType`** –

  A relationship type: its ends, label and the attributes it adds to them (THY-08 to THY-10).
- **`StructType`** –

  A struct type, and the base of every type with attributes (`AtlasStructType`, TRG-10 to TRG-13).

Functions:

- **`entity_types_and_all_sub_types`** –

  The entity types named and all their sub types (`getEntityTypesAndAllSubTypes`, THY-07).
- **`qualified_attribute_name`** –

  `Type.attribute`, or the name itself when it contains a dot or belongs to a root type (TRG-11, THY-05).
- **`referenced_entity_type`** –

  The entity type a type, an array of it or a map to it refers to, or None (TRG-12).
- **`type_of`** –

  The unresolved type of a definition, by its exact class (`addTypeWithNoRefResolve`).
- **`validate_relationship_def`** –

  Check the ends' cardinality and containers against the category (`validateAtlasRelationshipDef`, THY-08).

Attributes:

- **`CLASSIFICATION_ROOT`** –

  `__CLASSIFICATION_ROOT`; not registered, resolved by every registry (THY-05).
- **`CLASSIFICATION_ROOT_NAME`** –
- **`ENTITY_HEADER_ATTRIBUTES`** –
- **`ENTITY_ROOT`** –

  `__ENTITY_ROOT`; not registered, resolved by every registry (THY-05).
- **`ENTITY_ROOT_NAME`** –
- **`INTERNAL_TYPE_NAME`** –
- **`OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE`** –
- **`OPTION_SCHEMA_ATTRIBUTES`** –

### CLASSIFICATION\_ROOT

```
CLASSIFICATION_ROOT = ClassificationType(_root_classification_def())
```

`__CLASSIFICATION_ROOT`; not registered, resolved by every registry (THY-05).

### CLASSIFICATION\_ROOT\_NAME

```
CLASSIFICATION_ROOT_NAME = '__CLASSIFICATION_ROOT'
```

### ENTITY\_HEADER\_ATTRIBUTES

```
ENTITY_HEADER_ATTRIBUTES = ('name', 'description', 'owner', 'createTime')
```

### ENTITY\_ROOT

```
ENTITY_ROOT = EntityType(_root_entity_def())
```

`__ENTITY_ROOT`; not registered, resolved by every registry (THY-05).

### ENTITY\_ROOT\_NAME

```
ENTITY_ROOT_NAME = '__ENTITY_ROOT'
```

### INTERNAL\_TYPE\_NAME

```
INTERNAL_TYPE_NAME = '__internal'
```

### OPTION\_APPEND\_RELATIONSHIPS\_ON\_PARTIAL\_UPDATE

```
OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE = 'appendRelationshipsOnPartialUpdate'
```

### OPTION\_SCHEMA\_ATTRIBUTES

```
OPTION_SCHEMA_ATTRIBUTES = 'schemaAttributes'
```

### \_\_all\_\_

```
__all__ = [
    "CLASSIFICATION_ROOT",
    "CLASSIFICATION_ROOT_NAME",
    "ENTITY_HEADER_ATTRIBUTES",
    "ENTITY_ROOT",
    "ENTITY_ROOT_NAME",
    "INTERNAL_TYPE_NAME",
    "OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE",
    "OPTION_SCHEMA_ATTRIBUTES",
    "ArrayType",
    "AtlasAttribute",
    "AtlasType",
    "BuiltInType",
    "BusinessAttribute",
    "BusinessMetadataType",
    "ClassificationType",
    "EdgeDirection",
    "EntityType",
    "EnumType",
    "MapType",
    "ObjectIdType",
    "RelationshipType",
    "StructType",
    "entity_types_and_all_sub_types",
    "qualified_attribute_name",
    "referenced_entity_type",
    "type_of",
    "validate_relationship_def",
]
```

### ArrayType

```
ArrayType(
    element_type_name: str,
    *,
    element_type: AtlasType | None = None,
    min_count: int = COUNT_NOT_SET,
    max_count: int = COUNT_NOT_SET,
    cardinality: Cardinality = LIST,
)
```

Bases: `AtlasType`

`array<T>` with its cardinality and value counts (`AtlasArrayType`, TRG-02).

Methods:

- **`are_equal_values`** –

  A `SET` as sets, anything else as lists, each element compared by the element type (VAL-12).
- **`create_default_value`** –

  The element's default, `minCount` times when that is set, else once (VAL-12).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A string parsed as JSON, then each element normalised, nulls kept; None for a wrong count or element.
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, with the elements' `getNormalizedValueForUpdate`.
- **`is_valid_value`** –

  Null, or a list with a valid count of valid elements; a string is not (VAL-12).
- **`is_valid_value_for_update`** –

  As `is_valid_value`, with the elements' `isValidValueForUpdate`.
- **`type_for_attribute`** –

  This array, or a new one over the element's attribute type when that differs (TRG-11).
- **`validate_value`** –

  Report a wrong count, then validate each element as `<name>[<i>]` (VAL-12).
- **`validate_value_for_update`** –

  As `validate_value`, with the elements' `validateValueForUpdate`.

Attributes:

- **`cardinality`** –
- **`category`** –
- **`element_type`** –
- **`element_type_name`** –
- **`max_count`** –
- **`min_count`** –
- **`service_type`** –
- **`type_name`** –

#### cardinality

```
cardinality = cardinality
```

#### category

```
category = category
```

#### element\_type

```
element_type = element_type
```

#### element\_type\_name

```
element_type_name = element_type_name
```

#### max\_count

```
max_count = max_count
```

#### min\_count

```
min_count = min_count
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

A `SET` as sets, anything else as lists, each element compared by the element type (VAL-12).

#### create\_default\_value

```
create_default_value() -> list[Any]
```

The element's default, `minCount` times when that is set, else once (VAL-12).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> list[Any] | None
```

A string parsed as JSON, then each element normalised, nulls kept; None for a wrong count or element.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> list[Any] | None
```

As `get_normalized_value`, with the elements' `getNormalizedValueForUpdate`.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a list with a valid count of valid elements; a string is not (VAL-12).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`, with the elements' `isValidValueForUpdate`.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

This array, or a new one over the element's attribute type when that differs (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Report a wrong count, then validate each element as `<name>[<i>]` (VAL-12).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

As `validate_value`, with the elements' `validateValueForUpdate`.

### AtlasAttribute

```
AtlasAttribute(
    defined_in: StructType,
    attribute_def: AtlasAttributeDef,
    attribute_type: AtlasType,
    relationship_name: str | None = None,
    relationship_label: str | None = None,
)
```

A resolved attribute of a struct-like type (`AtlasStructType.AtlasAttribute`).

Methods:

- **`option_int`** –

  Option `name` as an integer, or None when blank (`getOptionInt`).
- **`option_set`** –

  Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).
- **`option_string`** –

  Option `name`, or None when blank (`getOptionString`).

Attributes:

- **`attribute_def`** –
- **`attribute_type`** –
- **`defined_in`** –
- **`inverse_ref_attribute`** (`AtlasAttribute | None`) –
- **`inverse_ref_attribute_name`** –
- **`is_legacy_attribute`** –
- **`is_object_ref`** –
- **`is_owned_ref`** –
- **`name`** –
- **`qualified_name`** –
- **`relationship_edge_direction`** –
- **`relationship_edge_label`** –
- **`relationship_name`** –

#### attribute\_def

```
attribute_def = attribute_def
```

#### attribute\_type

```
attribute_type = attribute_type.type_for_attribute()
```

#### defined\_in

```
defined_in = defined_in
```

#### inverse\_ref\_attribute

```
inverse_ref_attribute: AtlasAttribute | None = None
```

#### inverse\_ref\_attribute\_name

```
inverse_ref_attribute_name = next(
    (
        str(param)
        for constraint in constraints
        if constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF)
        and (param := constraint.get_param(CONSTRAINT_PARAM_ATTRIBUTE)) is not None
    ),
    None,
)
```

#### is\_legacy\_attribute

```
is_legacy_attribute = False
```

#### is\_object\_ref

```
is_object_ref = _holds_object_ids(self.attribute_type)
```

#### is\_owned\_ref

```
is_owned_ref = any(constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF) for constraint in constraints)
```

#### name

```
name = attribute_def.name
```

#### qualified\_name

```
qualified_name = qualified_attribute_name(defined_in.struct_def, str(attribute_def.name))
```

#### relationship\_edge\_direction

```
relationship_edge_direction = EdgeDirection.OUT
```

#### relationship\_edge\_label

```
relationship_edge_label = relationship_label or f'__{self.qualified_name}'
```

#### relationship\_name

```
relationship_name = relationship_name
```

#### option\_int

```
option_int(name: str) -> int | None
```

Option `name` as an integer, or None when blank (`getOptionInt`).

#### option\_set

```
option_set(name: str) -> list[str] | None
```

Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).

#### option\_string

```
option_string(name: str) -> str | None
```

Option `name`, or None when blank (`getOptionString`).

### AtlasType

```
AtlasType(type_name: str | None, category: TypeCategory, service_type: str | None)
```

A type: its name, category and service type, and how it checks, normalises and compares values.

The value methods are Java's, in snake\_case: `create_default_value` is `createDefaultValue`, `is_valid_value` is `isValidValue` and so on. A value is a Java value as DD-040 holds it.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The value an attribute of this type gets by default (`createDefaultValue()`).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  `value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Whether `value` is a value of this type (`isValidValue`).
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> Any
```

The value an attribute of this type gets by default (`createDefaultValue()`).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

`value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Whether `value` is a value of this type (`isValidValue`).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### BuiltInType

```
BuiltInType(type_name: str)
```

Bases: `AtlasType`

A primitive type such as `string` or `int`, of the `atlas_core` service type (TRG-01).

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The value an attribute of this type gets by default (`createDefaultValue()`).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  `value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Whether `value` is a value of this type (`isValidValue`).
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> Any
```

The value an attribute of this type gets by default (`createDefaultValue()`).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

`value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Whether `value` is a value of this type (`isValidValue`).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### BusinessAttribute

```
BusinessAttribute(
    attribute: AtlasAttribute,
    applicable_entity_types: list[EntityType],
    max_string_length: int = 0,
    valid_pattern: str | None = None,
)
```

Bases: `AtlasAttribute`

A business metadata attribute and the entity types it applies to (`AtlasBusinessAttribute`, THY-12).

Methods:

- **`option_int`** –

  Option `name` as an integer, or None when blank (`getOptionInt`).
- **`option_set`** –

  Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).
- **`option_string`** –

  Option `name`, or None when blank (`getOptionString`).

Attributes:

- **`applicable_entity_types`** –
- **`attribute_def`** –
- **`attribute_type`** –
- **`defined_in`** –
- **`inverse_ref_attribute`** (`AtlasAttribute | None`) –
- **`inverse_ref_attribute_name`** –
- **`is_legacy_attribute`** –
- **`is_object_ref`** –
- **`is_owned_ref`** –
- **`max_string_length`** –
- **`name`** –
- **`qualified_name`** –
- **`relationship_edge_direction`** –
- **`relationship_edge_label`** –
- **`relationship_name`** –
- **`valid_pattern`** –

#### applicable\_entity\_types

```
applicable_entity_types = applicable_entity_types
```

#### attribute\_def

```
attribute_def = attribute_def
```

#### attribute\_type

```
attribute_type = attribute_type.type_for_attribute()
```

#### defined\_in

```
defined_in = defined_in
```

#### inverse\_ref\_attribute

```
inverse_ref_attribute: AtlasAttribute | None = None
```

#### inverse\_ref\_attribute\_name

```
inverse_ref_attribute_name = next(
    (
        str(param)
        for constraint in constraints
        if constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF)
        and (param := constraint.get_param(CONSTRAINT_PARAM_ATTRIBUTE)) is not None
    ),
    None,
)
```

#### is\_legacy\_attribute

```
is_legacy_attribute = False
```

#### is\_object\_ref

```
is_object_ref = _holds_object_ids(self.attribute_type)
```

#### is\_owned\_ref

```
is_owned_ref = any(constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF) for constraint in constraints)
```

#### max\_string\_length

```
max_string_length = max_string_length
```

#### name

```
name = attribute_def.name
```

#### qualified\_name

```
qualified_name = qualified_attribute_name(defined_in.struct_def, str(attribute_def.name))
```

#### relationship\_edge\_direction

```
relationship_edge_direction = EdgeDirection.OUT
```

#### relationship\_edge\_label

```
relationship_edge_label = relationship_label or f'__{self.qualified_name}'
```

#### relationship\_name

```
relationship_name = relationship_name
```

#### valid\_pattern

```
valid_pattern = valid_pattern
```

#### option\_int

```
option_int(name: str) -> int | None
```

Option `name` as an integer, or None when blank (`getOptionInt`).

#### option\_set

```
option_set(name: str) -> list[str] | None
```

Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).

#### option\_string

```
option_string(name: str) -> str | None
```

Option `name`, or None when blank (`getOptionString`).

### BusinessMetadataType

```
BusinessMetadataType(business_metadata_def: AtlasBusinessMetadataDef)
```

Bases: `StructType`

A business metadata type: its attributes and the entity types they apply to (THY-12).

Methods:

- **`are_equal_values`** –

  Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`create_default_value`** –

  Null: business metadata has no instance (EVL-10).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  Null: business metadata has no instance (EVL-10).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_valid_value`** –

  Always: business metadata has no instance to check (EVL-10).
- **`is_valid_value_for_update`** –

  Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).
- **`normalize_attribute_values`** –

  Normalise the present own attributes and add the missing mandatory ones (EVL-04).
- **`normalize_attribute_values_for_update`** –

  Normalise the present own attributes for update; missing ones stay missing (EVL-03).
- **`populate_default_values`** –

  Set every mandatory own attribute to its default, replacing its value (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).
- **`validate_value_for_update`** –

  Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`business_metadata_def`** –
- **`category`** –
- **`service_type`** –
- **`struct_def`** –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### business\_metadata\_def

```
business_metadata_def = business_metadata_def
```

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).

Raises:

- `TypeError` –

  A string, on which Java's `getStructFromValue` fails with a `ClassCastException`.

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### create\_default\_value

```
create_default_value() -> None
```

Null: business metadata has no instance (EVL-10).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> None
```

Null: business metadata has no instance (EVL-10).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Always: business metadata has no instance to check (EVL-10).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise the present own attributes and add the missing mandatory ones (EVL-04).

A map is normalised at its top level, as Java's `normalizeAttributeValues(Map)` does.

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

Normalise the present own attributes for update; missing ones stay missing (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Set every mandatory own attribute to its default, replacing its value (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

### ClassificationType

```
ClassificationType(classification_def: AtlasClassificationDef)
```

Bases: `HierarchyType`

A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07).

Methods:

- **`are_equal_values`** –

  Equal for each super type and for this type (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`can_apply_to_entity_type`** –

  Whether the classification may be applied to `entity_type` (THY-07).
- **`create_default_value`** –

  A classification of this type with the defaults of its own and inherited mandatory attributes.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_sub_type_of`** –

  Whether `other` is among this type's super types, at any depth (THY-04).
- **`is_super_type_of`** –

  Whether `other` is among this type's sub types, at any depth (THY-04).
- **`is_valid_value`** –

  Valid for each super type, with valid validity periods, then for its own attributes (EVL-07).
- **`is_valid_value_for_update`** –

  As `is_valid_value`, for update (EVL-03, EVL-07).
- **`normalize_attribute_values`** –

  Normalise for each super type, then this type's own attributes (EVL-04).
- **`normalize_attribute_values_for_update`** –

  As `normalize_attribute_values`, for update (EVL-03).
- **`populate_default_values`** –

  Defaults for each super type's mandatory attributes, then this type's (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate for each super type, the validity periods, then the own attributes (EVL-07).
- **`validate_value_for_update`** –

  As `validate_value`, for update (EVL-03, EVL-07).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`all_sub_types`** (`list[str]`) –
- **`all_super_types`** (`list[str]`) –
- **`category`** –
- **`classification_def`** –
- **`entity_types`** (`list[str]`) –
- **`service_type`** –
- **`struct_def`** –
- **`sub_types`** (`list[str]`) –
- **`super_types`** (`list[HierarchyType]`) –
- **`type_and_all_sub_types`** (`list[str]`) –
- **`type_and_all_super_types`** (`list[str]`) –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### all\_sub\_types

```
all_sub_types: list[str] = []
```

#### all\_super\_types

```
all_super_types: list[str] = []
```

#### category

```
category = category
```

#### classification\_def

```
classification_def = classification_def
```

#### entity\_types

```
entity_types: list[str] = []
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### sub\_types

```
sub_types: list[str] = []
```

#### super\_types

```
super_types: list[HierarchyType] = []
```

#### type\_and\_all\_sub\_types

```
type_and_all_sub_types: list[str] = []
```

#### type\_and\_all\_super\_types

```
type_and_all_super_types: list[str] = []
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Equal for each super type and for this type (EVL-06).

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### can\_apply\_to\_entity\_type

```
can_apply_to_entity_type(entity_type: EntityType) -> bool
```

Whether the classification may be applied to `entity_type` (THY-07).

#### create\_default\_value

```
create_default_value() -> AtlasClassification
```

A classification of this type with the defaults of its own and inherited mandatory attributes.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_sub\_type\_of

```
is_sub_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's super types, at any depth (THY-04).

#### is\_super\_type\_of

```
is_super_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's sub types, at any depth (THY-04).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Valid for each super type, with valid validity periods, then for its own attributes (EVL-07).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`, for update (EVL-03, EVL-07).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise for each super type, then this type's own attributes (EVL-04).

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

As `normalize_attribute_values`, for update (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Defaults for each super type's mandatory attributes, then this type's (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate for each super type, the validity periods, then the own attributes (EVL-07).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

As `validate_value`, for update (EVL-03, EVL-07).

### EdgeDirection

Bases: `StrEnum`

Which way a relationship attribute's edge points (`AtlasRelationshipEdgeDirection`, THY-10).

Attributes:

- **`BOTH`** –
- **`IN`** –
- **`OUT`** –

#### BOTH

```
BOTH = 'BOTH'
```

#### IN

```
IN = 'IN'
```

#### OUT

```
OUT = 'OUT'
```

### EntityType

```
EntityType(entity_def: AtlasEntityDef)
```

Bases: `HierarchyType`

An entity type: its hierarchy, relationship and business attributes (THY-01 to THY-06, THY-10 to THY-12).

Methods:

- **`are_equal_values`** –

  Equal for each super type and for this type (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`business_attribute`** –

  The attribute `attribute_name` of business metadata `metadata_name` on this type (THY-12).
- **`create_default_value`** –

  An entity of this type, with a temporary GUID and its mandatory attributes' defaults (EVL-05).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_sub_type_of`** –

  Whether `other` is among this type's super types, at any depth (THY-04).
- **`is_super_type_of`** –

  Whether `other` is among this type's sub types, at any depth (THY-04).
- **`is_valid_value`** –

  Valid for each super type, for its own attributes and its relationship attributes (EVL-08).
- **`is_valid_value_for_update`** –

  Valid for update for each super type and its own attributes; relationship attributes are not checked.
- **`normalize_attribute_values`** –

  Normalise for each super type, the own attributes, then the relationship attributes (EVL-09).
- **`normalize_attribute_values_for_update`** –

  As `normalize_attribute_values`, for update (EVL-03, EVL-09).
- **`normalize_relationship_attribute_values`** –

  Normalise the value of each relationship attribute that holds object ids or entities (EVL-09).
- **`populate_default_values`** –

  Defaults for each super type's mandatory attributes, then this type's (EVL-05).
- **`relationship_attribute`** –

  The relationship attribute `name` of `relationship_type`, else of the first relationship (THY-10).
- **`type_for_attribute`** –

  An attribute holds an entity as `objectid` of this entity type (TRG-11).
- **`validate_value`** –

  Validate for each super type, the own attributes, then the relationship attributes (EVL-08).
- **`validate_value_for_update`** –

  Validate for update for each super type and the own attributes (EVL-03, EVL-08).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`all_sub_types`** (`list[str]`) –
- **`all_super_types`** (`list[str]`) –
- **`business_attributes`** (`dict[str, dict[str, BusinessAttribute]]`) –
- **`category`** –
- **`display_text_attribute`** –
- **`dyn_eval_attributes`** (`list[AtlasAttribute]`) –
- **`dyn_eval_trigger_attributes`** (`list[AtlasAttribute]`) –
- **`entity_def`** –
- **`header_attributes`** (`dict[str, AtlasAttribute]`) –
- **`is_internal`** –
- **`min_info_attributes`** (`dict[str, AtlasAttribute]`) –
- **`owned_ref_attributes`** (`list[AtlasAttribute]`) –
- **`parsed_templates`** (`dict[str, list[TemplateToken]]`) –
- **`relationship_attributes`** (`dict[str, dict[str, AtlasAttribute]]`) –
- **`service_type`** –
- **`struct_def`** –
- **`sub_types`** (`list[str]`) –
- **`super_types`** (`list[HierarchyType]`) –
- **`tag_propagation_edges`** (`list[str | None]`) –
- **`type_and_all_sub_types`** (`list[str]`) –
- **`type_and_all_super_types`** (`list[str]`) –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### all\_sub\_types

```
all_sub_types: list[str] = []
```

#### all\_super\_types

```
all_super_types: list[str] = []
```

#### business\_attributes

```
business_attributes: dict[str, dict[str, BusinessAttribute]] = {}
```

#### category

```
category = category
```

#### display\_text\_attribute

```
display_text_attribute = entity_def.get_option(OPTION_DISPLAY_TEXT_ATTRIBUTE)
```

#### dyn\_eval\_attributes

```
dyn_eval_attributes: list[AtlasAttribute] = []
```

#### dyn\_eval\_trigger\_attributes

```
dyn_eval_trigger_attributes: list[AtlasAttribute] = []
```

#### entity\_def

```
entity_def = entity_def
```

#### header\_attributes

```
header_attributes: dict[str, AtlasAttribute] = {}
```

#### is\_internal

```
is_internal = False
```

#### min\_info\_attributes

```
min_info_attributes: dict[str, AtlasAttribute] = {}
```

#### owned\_ref\_attributes

```
owned_ref_attributes: list[AtlasAttribute] = []
```

#### parsed\_templates

```
parsed_templates: dict[str, list[TemplateToken]] = {}
```

#### relationship\_attributes

```
relationship_attributes: dict[str, dict[str, AtlasAttribute]] = {}
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### sub\_types

```
sub_types: list[str] = []
```

#### super\_types

```
super_types: list[HierarchyType] = []
```

#### tag\_propagation\_edges

```
tag_propagation_edges: list[str | None] = []
```

#### type\_and\_all\_sub\_types

```
type_and_all_sub_types: list[str] = []
```

#### type\_and\_all\_super\_types

```
type_and_all_super_types: list[str] = []
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Equal for each super type and for this type (EVL-06).

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### business\_attribute

```
business_attribute(metadata_name: str, attribute_name: str) -> BusinessAttribute | None
```

The attribute `attribute_name` of business metadata `metadata_name` on this type (THY-12).

#### create\_default\_value

```
create_default_value() -> AtlasEntity
```

An entity of this type, with a temporary GUID and its mandatory attributes' defaults (EVL-05).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_sub\_type\_of

```
is_sub_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's super types, at any depth (THY-04).

#### is\_super\_type\_of

```
is_super_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's sub types, at any depth (THY-04).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Valid for each super type, for its own attributes and its relationship attributes (EVL-08).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

Valid for update for each super type and its own attributes; relationship attributes are not checked.

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise for each super type, the own attributes, then the relationship attributes (EVL-09).

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

As `normalize_attribute_values`, for update (EVL-03, EVL-09).

#### normalize\_relationship\_attribute\_values

```
normalize_relationship_attribute_values(value: StructValue, *, for_update: bool) -> None
```

Normalise the value of each relationship attribute that holds object ids or entities (EVL-09).

An entity's `relationshipAttributes`; a map at its top level, as Java's map overload does.

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Defaults for each super type's mandatory attributes, then this type's (EVL-05).

#### relationship\_attribute

```
relationship_attribute(name: str, relationship_type: str | None = None) -> AtlasAttribute | None
```

The relationship attribute `name` of `relationship_type`, else of the first relationship (THY-10).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

An attribute holds an entity as `objectid` of this entity type (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate for each super type, the own attributes, then the relationship attributes (EVL-08).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate for update for each super type and the own attributes (EVL-03, EVL-08).

### EnumType

```
EnumType(enum_def: AtlasEnumDef)
```

Bases: `AtlasType`

An enum type: its elements by value and ordinal, and its default (`AtlasEnumType`, TRG-14).

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The enum's default value: its `defaultValue`, else its first element's (TRG-14).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`element`** –

  The element with `value`, compared without case, or None (TRG-14).
- **`element_by_ordinal`** –

  The element with `ordinal`, or None (TRG-14).
- **`get_normalized_value`** –

  The value of the element whose value is the Java text of `value`, ignoring case; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value whose Java text is an element's value, ignoring case (VAL-11).
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`default_value`** –
- **`enum_def`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### default\_value

```
default_value = enum_def.default_value if enum_def.default_value is not None else first
```

#### enum\_def

```
enum_def = enum_def
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> str | None
```

The enum's default value: its `defaultValue`, else its first element's (TRG-14).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### element

```
element(value: str | None) -> AtlasEnumElementDef | None
```

The element with `value`, compared without case, or None (TRG-14).

#### element\_by\_ordinal

```
element_by_ordinal(ordinal: int | None) -> AtlasEnumElementDef | None
```

The element with `ordinal`, or None (TRG-14).

#### get\_normalized\_value

```
get_normalized_value(value: object) -> str | None
```

The value of the element whose value is the Java text of `value`, ignoring case; else None.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value whose Java text is an element's value, ignoring case (VAL-11).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### MapType

```
MapType(
    key_type_name: str, value_type_name: str, *, key_type: AtlasType | None = None, value_type: AtlasType | None = None
)
```

Bases: `AtlasType`

`map<K,V>` (`AtlasMapType`, TRG-02).

Methods:

- **`are_equal_values`** –

  Null equals an empty map; otherwise the same size and equal values by key (VAL-13).
- **`create_default_value`** –

  The key's default mapped to the value's, or an empty map when the key has no default (VAL-13).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A string parsed as JSON, then keys and values normalised, null values kept; None for a bad one.
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, with the values' `getNormalizedValueForUpdate`.
- **`is_valid_value`** –

  Null, or a map of valid keys and values; a string is not (VAL-13).
- **`is_valid_value_for_update`** –

  As `is_valid_value`, with the values' `isValidValueForUpdate`.
- **`type_for_attribute`** –

  This map, or a new one over the key's and value's attribute types when they differ (TRG-11).
- **`validate_value`** –

  Report each invalid key, and validate each value as `<name>.<key>` (VAL-13).
- **`validate_value_for_update`** –

  As `validate_value`, with the values' `validateValueForUpdate`.

Attributes:

- **`category`** –
- **`key_type`** –
- **`key_type_name`** –
- **`service_type`** –
- **`type_name`** –
- **`value_type`** –
- **`value_type_name`** –

#### category

```
category = category
```

#### key\_type

```
key_type = key_type
```

#### key\_type\_name

```
key_type_name = key_type_name
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### value\_type

```
value_type = value_type
```

#### value\_type\_name

```
value_type_name = value_type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Null equals an empty map; otherwise the same size and equal values by key (VAL-13).

#### create\_default\_value

```
create_default_value() -> dict[Any, Any]
```

The key's default mapped to the value's, or an empty map when the key has no default (VAL-13).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> dict[Any, Any] | None
```

A string parsed as JSON, then keys and values normalised, null values kept; None for a bad one.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> dict[Any, Any] | None
```

As `get_normalized_value`, with the values' `getNormalizedValueForUpdate`.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a map of valid keys and values; a string is not (VAL-13).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`, with the values' `isValidValueForUpdate`.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

This map, or a new one over the key's and value's attribute types when they differ (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Report each invalid key, and validate each value as `<name>.<key>` (VAL-13).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

As `validate_value`, with the values' `validateValueForUpdate`.

### ObjectIdType

```
ObjectIdType(object_type: str | None = ATLAS_TYPE_ASSET)
```

Bases: `AtlasType`

`objectid`: a reference to an entity of `object_type`, by GUID or by unique attributes.

Methods:

- **`are_equal_values`** –

  Equal by GUID, mapped through the assignments, when both or neither is assigned (VAL-10).
- **`create_default_value`** –

  An object id with the unassigned GUID `-1` and the object type.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  An object id as it is; a map that identifies an entity, read by Java's map constructor; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, an object id, or a map that identifies an entity.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`object_type`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### object\_type

```
object_type = object_type
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Equal by GUID, mapped through the assignments, when both or neither is assigned (VAL-10).

When only one GUID is assigned, the type names and unique attributes decide.

#### create\_default\_value

```
create_default_value() -> AtlasObjectId
```

An object id with the unassigned GUID `-1` and the object type.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> AtlasObjectId | None
```

An object id as it is; a map that identifies an entity, read by Java's map constructor; else None.

A map with a `relationshipType` key becomes a related object id.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, an object id, or a map that identifies an entity.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### RelationshipType

```
RelationshipType(relationship_def: AtlasRelationshipDef)
```

Bases: `StructType`

A relationship type: its ends, label and the attributes it adds to them (THY-08 to THY-10).

Methods:

- **`are_equal_values`** –

  Both null, or relationships equal as structs and by GUID, ends, label, tag propagation and status.
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`create_default_value`** –

  A struct of this type with the defaults of its mandatory attributes (EVL-05).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_valid_value`** –

  Null, or an `AtlasRelationship` with valid ends and, given end types, valid attributes (REL-02).
- **`is_valid_value_for_update`** –

  As `is_valid_value`: Atlas checks a relationship for update the same way (REL-02).
- **`normalize_attribute_values`** –

  Normalise the present own attributes and add the missing mandatory ones (EVL-04).
- **`normalize_attribute_values_for_update`** –

  Normalise the present own attributes for update; missing ones stay missing (EVL-03).
- **`populate_default_values`** –

  Set every mandatory own attribute to its default, replacing its value (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).
- **`validate_value_for_update`** –

  Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`category`** –
- **`end1_type`** (`EntityType | None`) –
- **`end2_type`** (`EntityType | None`) –
- **`has_legacy_attribute_end`** –
- **`relationship_def`** –
- **`relationship_label`** (`str | None`) –
- **`service_type`** –
- **`struct_def`** –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### category

```
category = category
```

#### end1\_type

```
end1_type: EntityType | None = None
```

#### end2\_type

```
end2_type: EntityType | None = None
```

#### has\_legacy\_attribute\_end

```
has_legacy_attribute_end = any(end is not None and end.is_legacy_attribute for end in ends)
```

#### relationship\_def

```
relationship_def = relationship_def
```

#### relationship\_label

```
relationship_label: str | None = None
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or relationships equal as structs and by GUID, ends, label, tag propagation and status.

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### create\_default\_value

```
create_default_value() -> AtlasStruct
```

A struct of this type with the defaults of its mandatory attributes (EVL-05).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or an `AtlasRelationship` with valid ends and, given end types, valid attributes (REL-02).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`: Atlas checks a relationship for update the same way (REL-02).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise the present own attributes and add the missing mandatory ones (EVL-04).

A map is normalised at its top level, as Java's `normalizeAttributeValues(Map)` does.

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

Normalise the present own attributes for update; missing ones stay missing (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Set every mandatory own attribute to its default, replacing its value (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

### StructType

```
StructType(struct_def: AtlasStructDef)
```

Bases: `AtlasType`

A struct type, and the base of every type with attributes (`AtlasStructType`, TRG-10 to TRG-13).

Methods:

- **`are_equal_values`** –

  Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`create_default_value`** –

  A struct of this type with the defaults of its mandatory attributes (EVL-05).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_valid_value`** –

  Null, or a struct or map whose own attributes are each valid or optionally absent (EVL-01).
- **`is_valid_value_for_update`** –

  Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).
- **`normalize_attribute_values`** –

  Normalise the present own attributes and add the missing mandatory ones (EVL-04).
- **`normalize_attribute_values_for_update`** –

  Normalise the present own attributes for update; missing ones stay missing (EVL-03).
- **`populate_default_values`** –

  Set every mandatory own attribute to its default, replacing its value (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).
- **`validate_value_for_update`** –

  Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`category`** –
- **`service_type`** –
- **`struct_def`** –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).

Raises:

- `TypeError` –

  A string, on which Java's `getStructFromValue` fails with a `ClassCastException`.

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### create\_default\_value

```
create_default_value() -> AtlasStruct
```

A struct of this type with the defaults of its mandatory attributes (EVL-05).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a struct or map whose own attributes are each valid or optionally absent (EVL-01).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise the present own attributes and add the missing mandatory ones (EVL-04).

A map is normalised at its top level, as Java's `normalizeAttributeValues(Map)` does.

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

Normalise the present own attributes for update; missing ones stay missing (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Set every mandatory own attribute to its default, replacing its value (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

### entity\_types\_and\_all\_sub\_types

```
entity_types_and_all_sub_types(names: list[str], registry: TypeRegistry) -> list[str]
```

The entity types named and all their sub types (`getEntityTypesAndAllSubTypes`, THY-07).

Raises:

- `AtlasError` –

  `TYPE_NAME_NOT_FOUND` for a name that is not an entity type.

### qualified\_attribute\_name

```
qualified_attribute_name(struct_def: AtlasStructDef, attribute_name: str) -> str
```

`Type.attribute`, or the name itself when it contains a dot or belongs to a root type (TRG-11, THY-05).

### referenced\_entity\_type

```
referenced_entity_type(type_: AtlasType) -> EntityType | None
```

The entity type a type, an array of it or a map to it refers to, or None (TRG-12).

### type\_of

```
type_of(typedef: AtlasBaseTypeDef) -> StructType | EnumType
```

The unresolved type of a definition, by its exact class (`addTypeWithNoRefResolve`).

### validate\_relationship\_def

```
validate_relationship_def(relationship_def: AtlasRelationshipDef) -> None
```

Check the ends' cardinality and containers against the category (`validateAtlasRelationshipDef`, THY-08).

Raises:

- `AtlasError` –

  The `RELATIONSHIPDEF_*` code of the first rule broken.

## aurelius\_atlas\_typesystem.atlas\_type

`AtlasType`: what every type has, its name and category, and the value contract (VAL-02, DD-041).

Classes:

- **`AtlasType`** –

  A type: its name, category and service type, and how it checks, normalises and compares values.

Functions:

- **`resolved`** –

  A type a containing type has resolved; it is resolved before its values or attribute type are asked for.
- **`type_name_of`** –

  The name of `type_`, which every resolved type has.

Attributes:

- **`UNIMPLEMENTED_VALUE_ERROR`** –

### UNIMPLEMENTED\_VALUE\_ERROR

```
UNIMPLEMENTED_VALUE_ERROR = '{type} has no value side yet (2.1c)'
```

### AtlasType

```
AtlasType(type_name: str | None, category: TypeCategory, service_type: str | None)
```

A type: its name, category and service type, and how it checks, normalises and compares values.

The value methods are Java's, in snake\_case: `create_default_value` is `createDefaultValue`, `is_valid_value` is `isValidValue` and so on. A value is a Java value as DD-040 holds it.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The value an attribute of this type gets by default (`createDefaultValue()`).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  `value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Whether `value` is a value of this type (`isValidValue`).
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> Any
```

The value an attribute of this type gets by default (`createDefaultValue()`).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

`value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Whether `value` is a value of this type (`isValidValue`).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### resolved

```
resolved(type_: AtlasType | None) -> AtlasType
```

A type a containing type has resolved; it is resolved before its values or attribute type are asked for.

Raises:

- `AtlasError` –

  `INTERNAL_ERROR` for an unresolved type.

### type\_name\_of

```
type_name_of(type_: AtlasType) -> str
```

The name of `type_`, which every resolved type has.

## aurelius\_atlas\_typesystem.struct\_type

`AtlasStructType`: a struct's attributes, as its definition resolves them (TRG-11, TRG-12, DD-041).

Type Aliases:

- **`StructValue`** –

  A struct value: an `AtlasStruct` (or subclass) or a map, as Java's struct types take.

Classes:

- **`StructType`** –

  A struct type, and the base of every type with attributes (`AtlasStructType`, TRG-10 to TRG-13).

Functions:

- **`contained_type`** –

  The element of an array or the value of a map; the type itself otherwise.
- **`referenced_entity_type`** –

  The entity type a type, an array of it or a map to it refers to, or None (TRG-12).
- **`relationship_attributes_of`** –

  `AtlasTypeUtil.toRelationshipAttributes`: a map's `relationshipAttributes` when it has a `typeName`.
- **`struct_attributes`** –

  `AtlasTypeUtil.toStructAttributes`: a map's `attributes` when it has a `typeName`, else the map.

Attributes:

- **`STRUCT_STRING_ERROR`** –

### STRUCT\_STRING\_ERROR

```
STRUCT_STRING_ERROR = "a string is no struct value: Java's getStructFromValue fails on it"
```

### StructValue

```
StructValue = AtlasStruct | dict[str, Any]
```

A struct value: an `AtlasStruct` (or subclass) or a map, as Java's struct types take.

### StructType

```
StructType(struct_def: AtlasStructDef)
```

Bases: `AtlasType`

A struct type, and the base of every type with attributes (`AtlasStructType`, TRG-10 to TRG-13).

Methods:

- **`are_equal_values`** –

  Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`create_default_value`** –

  A struct of this type with the defaults of its mandatory attributes (EVL-05).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_valid_value`** –

  Null, or a struct or map whose own attributes are each valid or optionally absent (EVL-01).
- **`is_valid_value_for_update`** –

  Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).
- **`normalize_attribute_values`** –

  Normalise the present own attributes and add the missing mandatory ones (EVL-04).
- **`normalize_attribute_values_for_update`** –

  Normalise the present own attributes for update; missing ones stay missing (EVL-03).
- **`populate_default_values`** –

  Set every mandatory own attribute to its default, replacing its value (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).
- **`validate_value_for_update`** –

  Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`category`** –
- **`service_type`** –
- **`struct_def`** –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).

Raises:

- `TypeError` –

  A string, on which Java's `getStructFromValue` fails with a `ClassCastException`.

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### create\_default\_value

```
create_default_value() -> AtlasStruct
```

A struct of this type with the defaults of its mandatory attributes (EVL-05).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a struct or map whose own attributes are each valid or optionally absent (EVL-01).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise the present own attributes and add the missing mandatory ones (EVL-04).

A map is normalised at its top level, as Java's `normalizeAttributeValues(Map)` does.

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

Normalise the present own attributes for update; missing ones stay missing (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Set every mandatory own attribute to its default, replacing its value (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

### contained\_type

```
contained_type(type_: AtlasType) -> AtlasType
```

The element of an array or the value of a map; the type itself otherwise.

### referenced\_entity\_type

```
referenced_entity_type(type_: AtlasType) -> EntityType | None
```

The entity type a type, an array of it or a map to it refers to, or None (TRG-12).

### relationship\_attributes\_of

```
relationship_attributes_of(value: Mapping[str, Any]) -> Mapping[str, Any] | None
```

`AtlasTypeUtil.toRelationshipAttributes`: a map's `relationshipAttributes` when it has a `typeName`.

### struct\_attributes

```
struct_attributes(value: Mapping[str, Any]) -> Mapping[str, Any]
```

`AtlasTypeUtil.toStructAttributes`: a map's `attributes` when it has a `typeName`, else the map.

## aurelius\_atlas\_typesystem.classification\_type

`AtlasClassificationType`: a classification, its hierarchy and its entity types (THY-06 to THY-08).

Classes:

- **`ClassificationType`** –

  A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07).

Functions:

- **`parse_time_boundary`** –

  `DateValidator.validate(text, "yyyy/MM/dd HH:mm:ss", zone)`: strict, the whole text, else None.
- **`validate_time_boundaries`** –

  `validateTimeBoundaries`: each validity period of a classification is valid (EVL-07).

Attributes:

- **`CLASSIFICATION_ROOT`** –

  `__CLASSIFICATION_ROOT`; not registered, resolved by every registry (THY-05).

### CLASSIFICATION\_ROOT

```
CLASSIFICATION_ROOT = ClassificationType(_root_classification_def())
```

`__CLASSIFICATION_ROOT`; not registered, resolved by every registry (THY-05).

### ClassificationType

```
ClassificationType(classification_def: AtlasClassificationDef)
```

Bases: `HierarchyType`

A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07).

Methods:

- **`are_equal_values`** –

  Equal for each super type and for this type (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`can_apply_to_entity_type`** –

  Whether the classification may be applied to `entity_type` (THY-07).
- **`create_default_value`** –

  A classification of this type with the defaults of its own and inherited mandatory attributes.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_sub_type_of`** –

  Whether `other` is among this type's super types, at any depth (THY-04).
- **`is_super_type_of`** –

  Whether `other` is among this type's sub types, at any depth (THY-04).
- **`is_valid_value`** –

  Valid for each super type, with valid validity periods, then for its own attributes (EVL-07).
- **`is_valid_value_for_update`** –

  As `is_valid_value`, for update (EVL-03, EVL-07).
- **`normalize_attribute_values`** –

  Normalise for each super type, then this type's own attributes (EVL-04).
- **`normalize_attribute_values_for_update`** –

  As `normalize_attribute_values`, for update (EVL-03).
- **`populate_default_values`** –

  Defaults for each super type's mandatory attributes, then this type's (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate for each super type, the validity periods, then the own attributes (EVL-07).
- **`validate_value_for_update`** –

  As `validate_value`, for update (EVL-03, EVL-07).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`all_sub_types`** (`list[str]`) –
- **`all_super_types`** (`list[str]`) –
- **`category`** –
- **`classification_def`** –
- **`entity_types`** (`list[str]`) –
- **`service_type`** –
- **`struct_def`** –
- **`sub_types`** (`list[str]`) –
- **`super_types`** (`list[HierarchyType]`) –
- **`type_and_all_sub_types`** (`list[str]`) –
- **`type_and_all_super_types`** (`list[str]`) –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### all\_sub\_types

```
all_sub_types: list[str] = []
```

#### all\_super\_types

```
all_super_types: list[str] = []
```

#### category

```
category = category
```

#### classification\_def

```
classification_def = classification_def
```

#### entity\_types

```
entity_types: list[str] = []
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### sub\_types

```
sub_types: list[str] = []
```

#### super\_types

```
super_types: list[HierarchyType] = []
```

#### type\_and\_all\_sub\_types

```
type_and_all_sub_types: list[str] = []
```

#### type\_and\_all\_super\_types

```
type_and_all_super_types: list[str] = []
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Equal for each super type and for this type (EVL-06).

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### can\_apply\_to\_entity\_type

```
can_apply_to_entity_type(entity_type: EntityType) -> bool
```

Whether the classification may be applied to `entity_type` (THY-07).

#### create\_default\_value

```
create_default_value() -> AtlasClassification
```

A classification of this type with the defaults of its own and inherited mandatory attributes.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_sub\_type\_of

```
is_sub_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's super types, at any depth (THY-04).

#### is\_super\_type\_of

```
is_super_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's sub types, at any depth (THY-04).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Valid for each super type, with valid validity periods, then for its own attributes (EVL-07).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`, for update (EVL-03, EVL-07).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise for each super type, then this type's own attributes (EVL-04).

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

As `normalize_attribute_values`, for update (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Defaults for each super type's mandatory attributes, then this type's (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate for each super type, the validity periods, then the own attributes (EVL-07).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

As `validate_value`, for update (EVL-03, EVL-07).

### parse\_time\_boundary

```
parse_time_boundary(text: str, zone: tzinfo) -> datetime | None
```

`DateValidator.validate(text, "yyyy/MM/dd HH:mm:ss", zone)`: strict, the whole text, else None.

Each number may be preceded by whitespace, as `SimpleDateFormat` skips it before a field.

### validate\_time\_boundaries

```
validate_time_boundaries(value: object, messages: list[str] | None) -> bool
```

`validateTimeBoundaries`: each validity period of a classification is valid (EVL-07).

A map has none: Java reads it with `AtlasClassification(Map)`, which takes no validity periods. Each message is added once.

## aurelius\_atlas\_typesystem.entity\_type

`AtlasEntityType`: an entity, its hierarchy, relationship and business attributes (THY-09 to THY-12).

Classes:

- **`EntityType`** –

  An entity type: its hierarchy, relationship and business attributes (THY-01 to THY-06, THY-10 to THY-12).

Functions:

- **`entity_types_and_all_sub_types`** –

  The entity types named and all their sub types (`getEntityTypesAndAllSubTypes`, THY-07).
- **`template_split`** –

  `templateSplit`: constants outside braces, `{name}` an attribute, `{a.b}` a dependent token (EWR-03).

Attributes:

- **`DYN_ATTRIBUTE_PREFIX`** –

  The entity type option naming a dynamic attribute: `dynAttribute:<name>`, its value the template.
- **`ENTITY_ROOT`** –

  `__ENTITY_ROOT`; not registered, resolved by every registry (THY-05).

### DYN\_ATTRIBUTE\_PREFIX

```
DYN_ATTRIBUTE_PREFIX = 'dynAttribute:'
```

The entity type option naming a dynamic attribute: `dynAttribute:<name>`, its value the template.

### ENTITY\_ROOT

```
ENTITY_ROOT = EntityType(_root_entity_def())
```

`__ENTITY_ROOT`; not registered, resolved by every registry (THY-05).

### EntityType

```
EntityType(entity_def: AtlasEntityDef)
```

Bases: `HierarchyType`

An entity type: its hierarchy, relationship and business attributes (THY-01 to THY-06, THY-10 to THY-12).

Methods:

- **`are_equal_values`** –

  Equal for each super type and for this type (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`business_attribute`** –

  The attribute `attribute_name` of business metadata `metadata_name` on this type (THY-12).
- **`create_default_value`** –

  An entity of this type, with a temporary GUID and its mandatory attributes' defaults (EVL-05).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_sub_type_of`** –

  Whether `other` is among this type's super types, at any depth (THY-04).
- **`is_super_type_of`** –

  Whether `other` is among this type's sub types, at any depth (THY-04).
- **`is_valid_value`** –

  Valid for each super type, for its own attributes and its relationship attributes (EVL-08).
- **`is_valid_value_for_update`** –

  Valid for update for each super type and its own attributes; relationship attributes are not checked.
- **`normalize_attribute_values`** –

  Normalise for each super type, the own attributes, then the relationship attributes (EVL-09).
- **`normalize_attribute_values_for_update`** –

  As `normalize_attribute_values`, for update (EVL-03, EVL-09).
- **`normalize_relationship_attribute_values`** –

  Normalise the value of each relationship attribute that holds object ids or entities (EVL-09).
- **`populate_default_values`** –

  Defaults for each super type's mandatory attributes, then this type's (EVL-05).
- **`relationship_attribute`** –

  The relationship attribute `name` of `relationship_type`, else of the first relationship (THY-10).
- **`type_for_attribute`** –

  An attribute holds an entity as `objectid` of this entity type (TRG-11).
- **`validate_value`** –

  Validate for each super type, the own attributes, then the relationship attributes (EVL-08).
- **`validate_value_for_update`** –

  Validate for update for each super type and the own attributes (EVL-03, EVL-08).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`all_sub_types`** (`list[str]`) –
- **`all_super_types`** (`list[str]`) –
- **`business_attributes`** (`dict[str, dict[str, BusinessAttribute]]`) –
- **`category`** –
- **`display_text_attribute`** –
- **`dyn_eval_attributes`** (`list[AtlasAttribute]`) –
- **`dyn_eval_trigger_attributes`** (`list[AtlasAttribute]`) –
- **`entity_def`** –
- **`header_attributes`** (`dict[str, AtlasAttribute]`) –
- **`is_internal`** –
- **`min_info_attributes`** (`dict[str, AtlasAttribute]`) –
- **`owned_ref_attributes`** (`list[AtlasAttribute]`) –
- **`parsed_templates`** (`dict[str, list[TemplateToken]]`) –
- **`relationship_attributes`** (`dict[str, dict[str, AtlasAttribute]]`) –
- **`service_type`** –
- **`struct_def`** –
- **`sub_types`** (`list[str]`) –
- **`super_types`** (`list[HierarchyType]`) –
- **`tag_propagation_edges`** (`list[str | None]`) –
- **`type_and_all_sub_types`** (`list[str]`) –
- **`type_and_all_super_types`** (`list[str]`) –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### all\_sub\_types

```
all_sub_types: list[str] = []
```

#### all\_super\_types

```
all_super_types: list[str] = []
```

#### business\_attributes

```
business_attributes: dict[str, dict[str, BusinessAttribute]] = {}
```

#### category

```
category = category
```

#### display\_text\_attribute

```
display_text_attribute = entity_def.get_option(OPTION_DISPLAY_TEXT_ATTRIBUTE)
```

#### dyn\_eval\_attributes

```
dyn_eval_attributes: list[AtlasAttribute] = []
```

#### dyn\_eval\_trigger\_attributes

```
dyn_eval_trigger_attributes: list[AtlasAttribute] = []
```

#### entity\_def

```
entity_def = entity_def
```

#### header\_attributes

```
header_attributes: dict[str, AtlasAttribute] = {}
```

#### is\_internal

```
is_internal = False
```

#### min\_info\_attributes

```
min_info_attributes: dict[str, AtlasAttribute] = {}
```

#### owned\_ref\_attributes

```
owned_ref_attributes: list[AtlasAttribute] = []
```

#### parsed\_templates

```
parsed_templates: dict[str, list[TemplateToken]] = {}
```

#### relationship\_attributes

```
relationship_attributes: dict[str, dict[str, AtlasAttribute]] = {}
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### sub\_types

```
sub_types: list[str] = []
```

#### super\_types

```
super_types: list[HierarchyType] = []
```

#### tag\_propagation\_edges

```
tag_propagation_edges: list[str | None] = []
```

#### type\_and\_all\_sub\_types

```
type_and_all_sub_types: list[str] = []
```

#### type\_and\_all\_super\_types

```
type_and_all_super_types: list[str] = []
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Equal for each super type and for this type (EVL-06).

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### business\_attribute

```
business_attribute(metadata_name: str, attribute_name: str) -> BusinessAttribute | None
```

The attribute `attribute_name` of business metadata `metadata_name` on this type (THY-12).

#### create\_default\_value

```
create_default_value() -> AtlasEntity
```

An entity of this type, with a temporary GUID and its mandatory attributes' defaults (EVL-05).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_sub\_type\_of

```
is_sub_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's super types, at any depth (THY-04).

#### is\_super\_type\_of

```
is_super_type_of(other: StructType | str | None) -> bool
```

Whether `other` is among this type's sub types, at any depth (THY-04).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Valid for each super type, for its own attributes and its relationship attributes (EVL-08).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

Valid for update for each super type and its own attributes; relationship attributes are not checked.

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise for each super type, the own attributes, then the relationship attributes (EVL-09).

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

As `normalize_attribute_values`, for update (EVL-03, EVL-09).

#### normalize\_relationship\_attribute\_values

```
normalize_relationship_attribute_values(value: StructValue, *, for_update: bool) -> None
```

Normalise the value of each relationship attribute that holds object ids or entities (EVL-09).

An entity's `relationshipAttributes`; a map at its top level, as Java's map overload does.

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Defaults for each super type's mandatory attributes, then this type's (EVL-05).

#### relationship\_attribute

```
relationship_attribute(name: str, relationship_type: str | None = None) -> AtlasAttribute | None
```

The relationship attribute `name` of `relationship_type`, else of the first relationship (THY-10).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

An attribute holds an entity as `objectid` of this entity type (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate for each super type, the own attributes, then the relationship attributes (EVL-08).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate for update for each super type and the own attributes (EVL-03, EVL-08).

### entity\_types\_and\_all\_sub\_types

```
entity_types_and_all_sub_types(names: list[str], registry: TypeRegistry) -> list[str]
```

The entity types named and all their sub types (`getEntityTypesAndAllSubTypes`, THY-07).

Raises:

- `AtlasError` –

  `TYPE_NAME_NOT_FOUND` for a name that is not an entity type.

### template\_split

```
template_split(template: str) -> list[TemplateToken]
```

`templateSplit`: constants outside braces, `{name}` an attribute, `{a.b}` a dependent token (EWR-03).

Text after the last brace, and a name whose brace is not closed, are dropped, as Java drops them.

## aurelius\_atlas\_typesystem.relationship\_type

`AtlasRelationshipType`: a relationship between two entity types and the attributes it adds (THY-10, THY-11).

Classes:

- **`RelationshipType`** –

  A relationship type: its ends, label and the attributes it adds to them (THY-08 to THY-10).

Functions:

- **`validate_relationship_def`** –

  Check the ends' cardinality and containers against the category (`validateAtlasRelationshipDef`, THY-08).

### RelationshipType

```
RelationshipType(relationship_def: AtlasRelationshipDef)
```

Bases: `StructType`

A relationship type: its ends, label and the attributes it adds to them (THY-08 to THY-10).

Methods:

- **`are_equal_values`** –

  Both null, or relationships equal as structs and by GUID, ends, label, tag propagation and status.
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`create_default_value`** –

  A struct of this type with the defaults of its mandatory attributes (EVL-05).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The struct or map, its attributes normalised, when it is valid; else None (EVL-04).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_valid_value`** –

  Null, or an `AtlasRelationship` with valid ends and, given end types, valid attributes (REL-02).
- **`is_valid_value_for_update`** –

  As `is_valid_value`: Atlas checks a relationship for update the same way (REL-02).
- **`normalize_attribute_values`** –

  Normalise the present own attributes and add the missing mandatory ones (EVL-04).
- **`normalize_attribute_values_for_update`** –

  Normalise the present own attributes for update; missing ones stay missing (EVL-03).
- **`populate_default_values`** –

  Set every mandatory own attribute to its default, replacing its value (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).
- **`validate_value_for_update`** –

  Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`category`** –
- **`end1_type`** (`EntityType | None`) –
- **`end2_type`** (`EntityType | None`) –
- **`has_legacy_attribute_end`** –
- **`relationship_def`** –
- **`relationship_label`** (`str | None`) –
- **`service_type`** –
- **`struct_def`** –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### category

```
category = category
```

#### end1\_type

```
end1_type: EntityType | None = None
```

#### end2\_type

```
end2_type: EntityType | None = None
```

#### has\_legacy\_attribute\_end

```
has_legacy_attribute_end = any(end is not None and end.is_legacy_attribute for end in ends)
```

#### relationship\_def

```
relationship_def = relationship_def
```

#### relationship\_label

```
relationship_label: str | None = None
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or relationships equal as structs and by GUID, ends, label, tag propagation and status.

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### create\_default\_value

```
create_default_value() -> AtlasStruct
```

A struct of this type with the defaults of its mandatory attributes (EVL-05).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

The struct or map, its attributes normalised, when it is valid; else None (EVL-04).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or an `AtlasRelationship` with valid ends and, given end types, valid attributes (REL-02).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`: Atlas checks a relationship for update the same way (REL-02).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise the present own attributes and add the missing mandatory ones (EVL-04).

A map is normalised at its top level, as Java's `normalizeAttributeValues(Map)` does.

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

Normalise the present own attributes for update; missing ones stay missing (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Set every mandatory own attribute to its default, replacing its value (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

### validate\_relationship\_def

```
validate_relationship_def(relationship_def: AtlasRelationshipDef) -> None
```

Check the ends' cardinality and containers against the category (`validateAtlasRelationshipDef`, THY-08).

Raises:

- `AtlasError` –

  The `RELATIONSHIPDEF_*` code of the first rule broken.

## aurelius\_atlas\_typesystem.business\_metadata\_type

`AtlasBusinessMetadataType`: business metadata and the entity types it applies to (THY-12).

Classes:

- **`BusinessAttribute`** –

  A business metadata attribute and the entity types it applies to (`AtlasBusinessAttribute`, THY-12).
- **`BusinessMetadataType`** –

  A business metadata type: its attributes and the entity types they apply to (THY-12).

### BusinessAttribute

```
BusinessAttribute(
    attribute: AtlasAttribute,
    applicable_entity_types: list[EntityType],
    max_string_length: int = 0,
    valid_pattern: str | None = None,
)
```

Bases: `AtlasAttribute`

A business metadata attribute and the entity types it applies to (`AtlasBusinessAttribute`, THY-12).

Methods:

- **`option_int`** –

  Option `name` as an integer, or None when blank (`getOptionInt`).
- **`option_set`** –

  Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).
- **`option_string`** –

  Option `name`, or None when blank (`getOptionString`).

Attributes:

- **`applicable_entity_types`** –
- **`attribute_def`** –
- **`attribute_type`** –
- **`defined_in`** –
- **`inverse_ref_attribute`** (`AtlasAttribute | None`) –
- **`inverse_ref_attribute_name`** –
- **`is_legacy_attribute`** –
- **`is_object_ref`** –
- **`is_owned_ref`** –
- **`max_string_length`** –
- **`name`** –
- **`qualified_name`** –
- **`relationship_edge_direction`** –
- **`relationship_edge_label`** –
- **`relationship_name`** –
- **`valid_pattern`** –

#### applicable\_entity\_types

```
applicable_entity_types = applicable_entity_types
```

#### attribute\_def

```
attribute_def = attribute_def
```

#### attribute\_type

```
attribute_type = attribute_type.type_for_attribute()
```

#### defined\_in

```
defined_in = defined_in
```

#### inverse\_ref\_attribute

```
inverse_ref_attribute: AtlasAttribute | None = None
```

#### inverse\_ref\_attribute\_name

```
inverse_ref_attribute_name = next(
    (
        str(param)
        for constraint in constraints
        if constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF)
        and (param := constraint.get_param(CONSTRAINT_PARAM_ATTRIBUTE)) is not None
    ),
    None,
)
```

#### is\_legacy\_attribute

```
is_legacy_attribute = False
```

#### is\_object\_ref

```
is_object_ref = _holds_object_ids(self.attribute_type)
```

#### is\_owned\_ref

```
is_owned_ref = any(constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF) for constraint in constraints)
```

#### max\_string\_length

```
max_string_length = max_string_length
```

#### name

```
name = attribute_def.name
```

#### qualified\_name

```
qualified_name = qualified_attribute_name(defined_in.struct_def, str(attribute_def.name))
```

#### relationship\_edge\_direction

```
relationship_edge_direction = EdgeDirection.OUT
```

#### relationship\_edge\_label

```
relationship_edge_label = relationship_label or f'__{self.qualified_name}'
```

#### relationship\_name

```
relationship_name = relationship_name
```

#### valid\_pattern

```
valid_pattern = valid_pattern
```

#### option\_int

```
option_int(name: str) -> int | None
```

Option `name` as an integer, or None when blank (`getOptionInt`).

#### option\_set

```
option_set(name: str) -> list[str] | None
```

Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).

#### option\_string

```
option_string(name: str) -> str | None
```

Option `name`, or None when blank (`getOptionString`).

### BusinessMetadataType

```
BusinessMetadataType(business_metadata_def: AtlasBusinessMetadataDef)
```

Bases: `StructType`

A business metadata type: its attributes and the entity types they apply to (THY-12).

Methods:

- **`are_equal_values`** –

  Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).
- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`create_default_value`** –

  Null: business metadata has no instance (EVL-10).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default, whatever value is given (EVL-05).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  Null: business metadata has no instance (EVL-10).
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, checked and normalised for update (EVL-03).
- **`is_valid_value`** –

  Always: business metadata has no instance to check (EVL-10).
- **`is_valid_value_for_update`** –

  Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).
- **`normalize_attribute_values`** –

  Normalise the present own attributes and add the missing mandatory ones (EVL-04).
- **`normalize_attribute_values_for_update`** –

  Normalise the present own attributes for update; missing ones stay missing (EVL-03).
- **`populate_default_values`** –

  Set every mandatory own attribute to its default, replacing its value (EVL-05).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).
- **`validate_value_for_update`** –

  Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`business_metadata_def`** –
- **`category`** –
- **`service_type`** –
- **`struct_def`** –
- **`type_name`** –
- **`unique_attributes`** (`dict[str, AtlasAttribute]`) –

#### all\_attributes

```
all_attributes: dict[str, AtlasAttribute] = {}
```

#### business\_metadata\_def

```
business_metadata_def = business_metadata_def
```

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### struct\_def

```
struct_def = struct_def
```

#### type\_name

```
type_name = type_name
```

#### unique\_attributes

```
unique_attributes: dict[str, AtlasAttribute] = {}
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).

Raises:

- `TypeError` –

  A string, on which Java's `getStructFromValue` fails with a `ClassCastException`.

#### attribute

```
attribute(name: str | None) -> AtlasAttribute | None
```

The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).

#### attribute\_type

```
attribute_type(name: str | None) -> AtlasType | None
```

The type of the attribute named `name`, or None (TRG-13).

#### create\_default\_value

```
create_default_value() -> None
```

Null: business metadata has no instance (EVL-10).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default, whatever value is given (EVL-05).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> None
```

Null: business metadata has no instance (EVL-10).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

As `get_normalized_value`, checked and normalised for update (EVL-03).

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Always: business metadata has no instance to check (EVL-10).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03).

#### normalize\_attribute\_values

```
normalize_attribute_values(value: StructValue) -> None
```

Normalise the present own attributes and add the missing mandatory ones (EVL-04).

A map is normalised at its top level, as Java's `normalizeAttributeValues(Map)` does.

#### normalize\_attribute\_values\_for\_update

```
normalize_attribute_values_for_update(value: StructValue) -> None
```

Normalise the present own attributes for update; missing ones stay missing (EVL-03).

#### populate\_default\_values

```
populate_default_values(struct: AtlasStruct) -> None
```

Set every mandatory own attribute to its default, replacing its value (EVL-05).

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Validate each own attribute as `<name>.<attribute>`; report missing mandatory ones (EVL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

Validate each present attribute with a type as `<name>.<attribute>`, for update (EVL-03).

## aurelius\_atlas\_typesystem.attribute

`AtlasStructType.AtlasAttribute`: an attribute as its type resolves it (TRG-11, DD-041).

Classes:

- **`AtlasAttribute`** –

  A resolved attribute of a struct-like type (`AtlasStructType.AtlasAttribute`).

Functions:

- **`qualified_attribute_name`** –

  `Type.attribute`, or the name itself when it contains a dot or belongs to a root type (TRG-11, THY-05).

### AtlasAttribute

```
AtlasAttribute(
    defined_in: StructType,
    attribute_def: AtlasAttributeDef,
    attribute_type: AtlasType,
    relationship_name: str | None = None,
    relationship_label: str | None = None,
)
```

A resolved attribute of a struct-like type (`AtlasStructType.AtlasAttribute`).

Methods:

- **`option_int`** –

  Option `name` as an integer, or None when blank (`getOptionInt`).
- **`option_set`** –

  Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).
- **`option_string`** –

  Option `name`, or None when blank (`getOptionString`).

Attributes:

- **`attribute_def`** –
- **`attribute_type`** –
- **`defined_in`** –
- **`inverse_ref_attribute`** (`AtlasAttribute | None`) –
- **`inverse_ref_attribute_name`** –
- **`is_legacy_attribute`** –
- **`is_object_ref`** –
- **`is_owned_ref`** –
- **`name`** –
- **`qualified_name`** –
- **`relationship_edge_direction`** –
- **`relationship_edge_label`** –
- **`relationship_name`** –

#### attribute\_def

```
attribute_def = attribute_def
```

#### attribute\_type

```
attribute_type = attribute_type.type_for_attribute()
```

#### defined\_in

```
defined_in = defined_in
```

#### inverse\_ref\_attribute

```
inverse_ref_attribute: AtlasAttribute | None = None
```

#### inverse\_ref\_attribute\_name

```
inverse_ref_attribute_name = next(
    (
        str(param)
        for constraint in constraints
        if constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF)
        and (param := constraint.get_param(CONSTRAINT_PARAM_ATTRIBUTE)) is not None
    ),
    None,
)
```

#### is\_legacy\_attribute

```
is_legacy_attribute = False
```

#### is\_object\_ref

```
is_object_ref = _holds_object_ids(self.attribute_type)
```

#### is\_owned\_ref

```
is_owned_ref = any(constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF) for constraint in constraints)
```

#### name

```
name = attribute_def.name
```

#### qualified\_name

```
qualified_name = qualified_attribute_name(defined_in.struct_def, str(attribute_def.name))
```

#### relationship\_edge\_direction

```
relationship_edge_direction = EdgeDirection.OUT
```

#### relationship\_edge\_label

```
relationship_edge_label = relationship_label or f'__{self.qualified_name}'
```

#### relationship\_name

```
relationship_name = relationship_name
```

#### option\_int

```
option_int(name: str) -> int | None
```

Option `name` as an integer, or None when blank (`getOptionInt`).

#### option\_set

```
option_set(name: str) -> list[str] | None
```

Option `name` read as a JSON array of names, or None when blank or not an array (`getOptionSet`).

#### option\_string

```
option_string(name: str) -> str | None
```

Option `name`, or None when blank (`getOptionString`).

### qualified\_attribute\_name

```
qualified_attribute_name(struct_def: AtlasStructDef, attribute_name: str) -> str
```

`Type.attribute`, or the name itself when it contains a dot or belongs to a root type (TRG-11, THY-05).

## aurelius\_atlas\_typesystem.enum\_type

`AtlasEnumType`: an enum's elements, by value and ordinal, and its values (TRG-14, VAL-11).

Classes:

- **`EnumType`** –

  An enum type: its elements by value and ordinal, and its default (`AtlasEnumType`, TRG-14).

### EnumType

```
EnumType(enum_def: AtlasEnumDef)
```

Bases: `AtlasType`

An enum type: its elements by value and ordinal, and its default (`AtlasEnumType`, TRG-14).

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The enum's default value: its `defaultValue`, else its first element's (TRG-14).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`element`** –

  The element with `value`, compared without case, or None (TRG-14).
- **`element_by_ordinal`** –

  The element with `ordinal`, or None (TRG-14).
- **`get_normalized_value`** –

  The value of the element whose value is the Java text of `value`, ignoring case; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value whose Java text is an element's value, ignoring case (VAL-11).
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`default_value`** –
- **`enum_def`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### default\_value

```
default_value = enum_def.default_value if enum_def.default_value is not None else first
```

#### enum\_def

```
enum_def = enum_def
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> str | None
```

The enum's default value: its `defaultValue`, else its first element's (TRG-14).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### element

```
element(value: str | None) -> AtlasEnumElementDef | None
```

The element with `value`, compared without case, or None (TRG-14).

#### element\_by\_ordinal

```
element_by_ordinal(ordinal: int | None) -> AtlasEnumElementDef | None
```

The element with `ordinal`, or None (TRG-14).

#### get\_normalized\_value

```
get_normalized_value(value: object) -> str | None
```

The value of the element whose value is the Java text of `value`, ignoring case; else None.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value whose Java text is an element's value, ignoring case (VAL-11).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

## aurelius\_atlas\_typesystem.array\_type

`AtlasArrayType`: `array<T>`, its counts and cardinality, and its values (TRG-02, VAL-12).

Classes:

- **`ArrayType`** –

  `array<T>` with its cardinality and value counts (`AtlasArrayType`, TRG-02).

### ArrayType

```
ArrayType(
    element_type_name: str,
    *,
    element_type: AtlasType | None = None,
    min_count: int = COUNT_NOT_SET,
    max_count: int = COUNT_NOT_SET,
    cardinality: Cardinality = LIST,
)
```

Bases: `AtlasType`

`array<T>` with its cardinality and value counts (`AtlasArrayType`, TRG-02).

Methods:

- **`are_equal_values`** –

  A `SET` as sets, anything else as lists, each element compared by the element type (VAL-12).
- **`create_default_value`** –

  The element's default, `minCount` times when that is set, else once (VAL-12).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A string parsed as JSON, then each element normalised, nulls kept; None for a wrong count or element.
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, with the elements' `getNormalizedValueForUpdate`.
- **`is_valid_value`** –

  Null, or a list with a valid count of valid elements; a string is not (VAL-12).
- **`is_valid_value_for_update`** –

  As `is_valid_value`, with the elements' `isValidValueForUpdate`.
- **`type_for_attribute`** –

  This array, or a new one over the element's attribute type when that differs (TRG-11).
- **`validate_value`** –

  Report a wrong count, then validate each element as `<name>[<i>]` (VAL-12).
- **`validate_value_for_update`** –

  As `validate_value`, with the elements' `validateValueForUpdate`.

Attributes:

- **`cardinality`** –
- **`category`** –
- **`element_type`** –
- **`element_type_name`** –
- **`max_count`** –
- **`min_count`** –
- **`service_type`** –
- **`type_name`** –

#### cardinality

```
cardinality = cardinality
```

#### category

```
category = category
```

#### element\_type

```
element_type = element_type
```

#### element\_type\_name

```
element_type_name = element_type_name
```

#### max\_count

```
max_count = max_count
```

#### min\_count

```
min_count = min_count
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

A `SET` as sets, anything else as lists, each element compared by the element type (VAL-12).

#### create\_default\_value

```
create_default_value() -> list[Any]
```

The element's default, `minCount` times when that is set, else once (VAL-12).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> list[Any] | None
```

A string parsed as JSON, then each element normalised, nulls kept; None for a wrong count or element.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> list[Any] | None
```

As `get_normalized_value`, with the elements' `getNormalizedValueForUpdate`.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a list with a valid count of valid elements; a string is not (VAL-12).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`, with the elements' `isValidValueForUpdate`.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

This array, or a new one over the element's attribute type when that differs (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Report a wrong count, then validate each element as `<name>[<i>]` (VAL-12).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

As `validate_value`, with the elements' `validateValueForUpdate`.

## aurelius\_atlas\_typesystem.map\_type

`AtlasMapType`: `map<K,V>` and its values (TRG-02, VAL-13).

Classes:

- **`MapType`** –

  `map<K,V>` (`AtlasMapType`, TRG-02).

### MapType

```
MapType(
    key_type_name: str, value_type_name: str, *, key_type: AtlasType | None = None, value_type: AtlasType | None = None
)
```

Bases: `AtlasType`

`map<K,V>` (`AtlasMapType`, TRG-02).

Methods:

- **`are_equal_values`** –

  Null equals an empty map; otherwise the same size and equal values by key (VAL-13).
- **`create_default_value`** –

  The key's default mapped to the value's, or an empty map when the key has no default (VAL-13).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A string parsed as JSON, then keys and values normalised, null values kept; None for a bad one.
- **`get_normalized_value_for_update`** –

  As `get_normalized_value`, with the values' `getNormalizedValueForUpdate`.
- **`is_valid_value`** –

  Null, or a map of valid keys and values; a string is not (VAL-13).
- **`is_valid_value_for_update`** –

  As `is_valid_value`, with the values' `isValidValueForUpdate`.
- **`type_for_attribute`** –

  This map, or a new one over the key's and value's attribute types when they differ (TRG-11).
- **`validate_value`** –

  Report each invalid key, and validate each value as `<name>.<key>` (VAL-13).
- **`validate_value_for_update`** –

  As `validate_value`, with the values' `validateValueForUpdate`.

Attributes:

- **`category`** –
- **`key_type`** –
- **`key_type_name`** –
- **`service_type`** –
- **`type_name`** –
- **`value_type`** –
- **`value_type_name`** –

#### category

```
category = category
```

#### key\_type

```
key_type = key_type
```

#### key\_type\_name

```
key_type_name = key_type_name
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### value\_type

```
value_type = value_type
```

#### value\_type\_name

```
value_type_name = value_type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Null equals an empty map; otherwise the same size and equal values by key (VAL-13).

#### create\_default\_value

```
create_default_value() -> dict[Any, Any]
```

The key's default mapped to the value's, or an empty map when the key has no default (VAL-13).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> dict[Any, Any] | None
```

A string parsed as JSON, then keys and values normalised, null values kept; None for a bad one.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> dict[Any, Any] | None
```

As `get_normalized_value`, with the values' `getNormalizedValueForUpdate`.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a map of valid keys and values; a string is not (VAL-13).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

As `is_valid_value`, with the values' `isValidValueForUpdate`.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

This map, or a new one over the key's and value's attribute types when they differ (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Report each invalid key, and validate each value as `<name>.<key>` (VAL-13).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

As `validate_value`, with the values' `validateValueForUpdate`.

## aurelius\_atlas\_typesystem.builtin

Atlas's built-in types, one module per nested class of `AtlasBuiltInTypes` (DD-041).

Modules:

- **`big_decimal_type`** –

  `AtlasBuiltInTypes.AtlasBigDecimalType` (VAL-07).
- **`big_integer_type`** –

  `AtlasBuiltInTypes.AtlasBigIntegerType` (VAL-06).
- **`boolean_type`** –

  `AtlasBuiltInTypes.AtlasBooleanType` (VAL-03).
- **`builtin_type`** –

  `AtlasBuiltInTypes`: what the primitive types share (TRG-01).
- **`byte_type`** –

  `AtlasBuiltInTypes.AtlasByteType` (VAL-04).
- **`date_type`** –

  `AtlasBuiltInTypes.AtlasDateType` (VAL-08).
- **`double_type`** –

  `AtlasBuiltInTypes.AtlasDoubleType` (VAL-05).
- **`float_type`** –

  `AtlasBuiltInTypes.AtlasFloatType` (VAL-05).
- **`floating_type`** –

  What `AtlasFloatType` and `AtlasDoubleType` share (VAL-05).
- **`int_type`** –

  `AtlasBuiltInTypes.AtlasIntType` (VAL-04).
- **`integral_type`** –

  What `AtlasByteType`, `AtlasShortType`, `AtlasIntType` and `AtlasLongType` share (VAL-04).
- **`long_type`** –

  `AtlasBuiltInTypes.AtlasLongType` (VAL-04).
- **`object_id_type`** –

  `AtlasBuiltInTypes.AtlasObjectIdType` (VAL-10).
- **`short_type`** –

  `AtlasBuiltInTypes.AtlasShortType` (VAL-04).
- **`string_type`** –

  `AtlasBuiltInTypes.AtlasStringType` (VAL-09).

Classes:

- **`BigDecimalType`** –

  `bigdecimal`: any number, or a string Java's `BigDecimal` parses, with its digits kept.
- **`BigIntegerType`** –

  `biginteger`: any number or numeric string, truncated toward zero.
- **`BooleanType`** –

  `boolean`: a boolean, or `true` or `false` in any case.
- **`BuiltInType`** –

  A primitive type such as `string` or `int`, of the `atlas_core` service type (TRG-01).
- **`ByteType`** –

  `byte`: a 8-bit Java integer.
- **`DateType`** –

  `date`: a number of milliseconds since the epoch, or a date in Atlas's serialized format, in UTC.
- **`DoubleType`** –

  `double`: a number within ±`Double.MAX_VALUE`, held as a Python `float`.
- **`FloatType`** –

  `float`: a number within ±`Float.MAX_VALUE`, held as the shortest decimal of its 32-bit value.
- **`IntType`** –

  `int`: a 32-bit Java integer.
- **`LongType`** –

  `long`: a 64-bit Java integer.
- **`ObjectIdType`** –

  `objectid`: a reference to an entity of `object_type`, by GUID or by unique attributes.
- **`ShortType`** –

  `short`: a 16-bit Java integer.
- **`StringType`** –

  `string`: every value, as Java's text of it.

Attributes:

- **`PRIMITIVE_TYPES`** (`tuple[Callable[[], BuiltInType], ...]`) –

  The primitive types, `string` and `date`, in `AtlasTypeRegistry`'s order; `objectid` is apart.

### PRIMITIVE\_TYPES

```
PRIMITIVE_TYPES: tuple[Callable[[], BuiltInType], ...] = (
    BooleanType,
    ByteType,
    ShortType,
    IntType,
    LongType,
    FloatType,
    DoubleType,
    BigIntegerType,
    BigDecimalType,
    DateType,
    StringType,
)
```

The primitive types, `string` and `date`, in `AtlasTypeRegistry`'s order; `objectid` is apart.

### \_\_all\_\_

```
__all__ = [
    "PRIMITIVE_TYPES",
    "BigDecimalType",
    "BigIntegerType",
    "BooleanType",
    "BuiltInType",
    "ByteType",
    "DateType",
    "DoubleType",
    "FloatType",
    "IntType",
    "LongType",
    "ObjectIdType",
    "ShortType",
    "StringType",
]
```

### BigDecimalType

```
BigDecimalType()
```

Bases: `BuiltInType`

`bigdecimal`: any number, or a string Java's `BigDecimal` parses, with its digits kept.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  0\.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A decimal as it is; a `BigInteger` exactly; 0 as `0`; another number by `BigDecimal.valueOf`.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null or any number; otherwise a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> Decimal
```

0\.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Decimal | None
```

A decimal as it is; a `BigInteger` exactly; 0 as `0`; another number by `BigDecimal.valueOf`.

Raises:

- `ValueError` –

  A NaN or infinite double, which `BigDecimal.valueOf` rejects.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null or any number; otherwise a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### BigIntegerType

```
BigIntegerType()
```

Bases: `BuiltInType`

`biginteger`: any number or numeric string, truncated toward zero.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  0\.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  An integer as it is; a decimal truncated; a double's `longValue`; a string `BigDecimal` parses.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> int
```

0\.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> int | None
```

An integer as it is; a decimal truncated; a double's `longValue`; a string `BigDecimal` parses.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### BooleanType

```
BooleanType()
```

Bases: `BuiltInType`

`boolean`: a boolean, or `true` or `false` in any case.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  `false`.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A boolean as it is; the string `true` or `false`, ignoring case; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> bool
```

`false`.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> bool | None
```

A boolean as it is; the string `true` or `false`, ignoring case; else None.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### BuiltInType

```
BuiltInType(type_name: str)
```

Bases: `AtlasType`

A primitive type such as `string` or `int`, of the `atlas_core` service type (TRG-01).

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The value an attribute of this type gets by default (`createDefaultValue()`).
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  `value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Whether `value` is a value of this type (`isValidValue`).
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> Any
```

The value an attribute of this type gets by default (`createDefaultValue()`).

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> Any
```

`value` as this type holds it, or None when it is not a value of this type (`getNormalizedValue`).

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Whether `value` is a value of this type (`isValidValue`).

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### ByteType

```
ByteType()
```

Bases: `IntegralType`

`byte`: a 8-bit Java integer.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  0\.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The integer of a number in range, or of a string Java's `valueOf` parses; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`max_value`** –
- **`min_value`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### max\_value

```
max_value = 2 ** (bits - 1) - 1
```

#### min\_value

```
min_value = -2 ** (bits - 1)
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> int
```

0\.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> int | None
```

The integer of a number in range, or of a string Java's `valueOf` parses; else None.

Raises:

- `ValueError` –

  A NaN or infinite double for `long`, as Java's `toBigInteger` fails on it.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### DateType

```
DateType()
```

Bases: `BuiltInType`

`date`: a number of milliseconds since the epoch, or a date in Atlas's serialized format, in UTC.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The epoch.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A date as it is; a number's `longValue` in milliseconds; a string parsed leniently, else as a long.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, a date, a number or the empty string; otherwise a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> datetime
```

The epoch.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> datetime | None
```

A date as it is; a number's `longValue` in milliseconds; a string parsed leniently, else as a long.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, a date, a number or the empty string; otherwise a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### DoubleType

```
DoubleType()
```

Bases: `FloatingType`

`double`: a number within ±`Double.MAX_VALUE`, held as a Python `float`.

Methods:

- **`are_equal_values`** –

  Both null, or both normalise and differ by less than 1e-8 (VAL-05).
- **`create_default_value`** –

  0.0.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A number in range, or a parsed string, that is not infinite; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or both normalise and differ by less than 1e-8 (VAL-05).

#### create\_default\_value

```
create_default_value() -> float
```

0.0.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> float | None
```

A number in range, or a parsed string, that is not infinite; else None.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### FloatType

```
FloatType()
```

Bases: `FloatingType`

`float`: a number within ±`Float.MAX_VALUE`, held as the shortest decimal of its 32-bit value.

Methods:

- **`are_equal_values`** –

  Both null, or both normalise and differ by less than 1e-8 (VAL-05).
- **`create_default_value`** –

  0.0.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  A number in range, or a parsed string, that is not infinite; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Both null, or both normalise and differ by less than 1e-8 (VAL-05).

#### create\_default\_value

```
create_default_value() -> float
```

0.0.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> float | None
```

A number in range, or a parsed string, that is not infinite; else None.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### IntType

```
IntType()
```

Bases: `IntegralType`

`int`: a 32-bit Java integer.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  0\.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The integer of a number in range, or of a string Java's `valueOf` parses; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`max_value`** –
- **`min_value`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### max\_value

```
max_value = 2 ** (bits - 1) - 1
```

#### min\_value

```
min_value = -2 ** (bits - 1)
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> int
```

0\.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> int | None
```

The integer of a number in range, or of a string Java's `valueOf` parses; else None.

Raises:

- `ValueError` –

  A NaN or infinite double for `long`, as Java's `toBigInteger` fails on it.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### LongType

```
LongType()
```

Bases: `IntegralType`

`long`: a 64-bit Java integer.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  0\.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The integer of a number in range, or of a string Java's `valueOf` parses; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`max_value`** –
- **`min_value`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### max\_value

```
max_value = 2 ** (bits - 1) - 1
```

#### min\_value

```
min_value = -2 ** (bits - 1)
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> int
```

0\.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> int | None
```

The integer of a number in range, or of a string Java's `valueOf` parses; else None.

Raises:

- `ValueError` –

  A NaN or infinite double for `long`, as Java's `toBigInteger` fails on it.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### ObjectIdType

```
ObjectIdType(object_type: str | None = ATLAS_TYPE_ASSET)
```

Bases: `AtlasType`

`objectid`: a reference to an entity of `object_type`, by GUID or by unique attributes.

Methods:

- **`are_equal_values`** –

  Equal by GUID, mapped through the assignments, when both or neither is assigned (VAL-10).
- **`create_default_value`** –

  An object id with the unassigned GUID `-1` and the object type.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  An object id as it is; a map that identifies an entity, read by Java's map constructor; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, an object id, or a map that identifies an entity.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`object_type`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### object\_type

```
object_type = object_type
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

Equal by GUID, mapped through the assignments, when both or neither is assigned (VAL-10).

When only one GUID is assigned, the type names and unique attributes decide.

#### create\_default\_value

```
create_default_value() -> AtlasObjectId
```

An object id with the unassigned GUID `-1` and the object type.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> AtlasObjectId | None
```

An object id as it is; a map that identifies an entity, read by Java's map constructor; else None.

A map with a `relationshipType` key becomes a related object id.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, an object id, or a map that identifies an entity.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### ShortType

```
ShortType()
```

Bases: `IntegralType`

`short`: a 16-bit Java integer.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  0\.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  The default of an optional attribute; the default, unless a type says otherwise.
- **`get_normalized_value`** –

  The integer of a number in range, or of a string Java's `valueOf` parses; else None.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Null, or a value that normalises.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`max_value`** –
- **`min_value`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### max\_value

```
max_value = 2 ** (bits - 1) - 1
```

#### min\_value

```
min_value = -2 ** (bits - 1)
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> int
```

0\.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> Any
```

The default of an optional attribute; the default, unless a type says otherwise.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> int | None
```

The integer of a number in range, or of a string Java's `valueOf` parses; else None.

Raises:

- `ValueError` –

  A NaN or infinite double for `long`, as Java's `toBigInteger` fails on it.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Null, or a value that normalises.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

### StringType

```
StringType()
```

Bases: `BuiltInType`

`string`: every value, as Java's text of it.

Methods:

- **`are_equal_values`** –

  `areEqualValues`: both null, or both normalise to equal values (VAL-02).
- **`create_default_value`** –

  The empty string.
- **`create_default_value_of`** –

  `createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).
- **`create_optional_default_value`** –

  Null: an optional string attribute has no default.
- **`get_normalized_value`** –

  `obj.toString()`: Java's text of the value, or None for null.
- **`get_normalized_value_for_update`** –

  `getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.
- **`is_valid_value`** –

  Always.
- **`is_valid_value_for_update`** –

  `isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).
- **`validate_value`** –

  Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).
- **`validate_value_for_update`** –

  `validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

Attributes:

- **`category`** –
- **`service_type`** –
- **`type_name`** –

#### category

```
category = category
```

#### service\_type

```
service_type = service_type
```

#### type\_name

```
type_name = type_name
```

#### are\_equal\_values

```
are_equal_values(left: object, right: object, guid_assignments: dict[str, str] | None) -> bool
```

`areEqualValues`: both null, or both normalise to equal values (VAL-02).

#### create\_default\_value

```
create_default_value() -> str
```

The empty string.

#### create\_default\_value\_of

```
create_default_value_of(value: object) -> Any
```

`createDefaultValue(Object)`: the default for null, else the normalised value (VAL-02).

#### create\_optional\_default\_value

```
create_optional_default_value() -> None
```

Null: an optional string attribute has no default.

#### get\_normalized\_value

```
get_normalized_value(value: object) -> str | None
```

`obj.toString()`: Java's text of the value, or None for null.

#### get\_normalized\_value\_for\_update

```
get_normalized_value_for_update(value: object) -> Any
```

`getNormalizedValueForUpdate`: as `get_normalized_value`, unless a type says otherwise.

#### is\_valid\_value

```
is_valid_value(value: object) -> bool
```

Always.

#### is\_valid\_value\_for\_update

```
is_valid_value_for_update(value: object) -> bool
```

`isValidValueForUpdate`: as `is_valid_value`, unless a type says otherwise.

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

#### validate\_value

```
validate_value(value: object, name: str, messages: list[str]) -> bool
```

Whether `value` is valid; if not, add `<name>=<value>: invalid value for type <type>` (VAL-02).

#### validate\_value\_for\_update

```
validate_value_for_update(value: object, name: str, messages: list[str]) -> bool
```

`validateValueForUpdate`: as `validate_value`, unless a type says otherwise.

## aurelius\_atlas\_typesystem.java

Java's number conversions, on Java values held as Python values (DD-040).

A Java `Integer`, `Long` or `BigInteger` is an `int`, a `BigDecimal` a `Decimal`, a `Double` a `float` and a `Float` a `float` holding the shortest decimal of its 32-bit value. A `bool` is a Java `Boolean`, never a number. Each function is named after the Java method it ports.

Type Aliases:

- **`JavaNumber`** –

Functions:

- **`big_decimal_value_of`** –

  `BigDecimal.valueOf(double)`: the decimal of `Double.toString` (`5` becomes `5.0`).
- **`double_value`** –

  `Number.doubleValue`: the number as Java's `double` (an infinity beyond its range).
- **`float_value`** –

  `Number.floatValue`: the number as Java's `float` (an infinity beyond its range).
- **`is_long`** –

  Whether `value` is an integer Jackson reads as an `Integer` or a `Long`, not a `BigInteger`.
- **`is_number`** –

  `value instanceof Number`: an `int`, `float` or `Decimal`, but not a `bool`.
- **`is_valid_time_zone`** –

  `AtlasClassificationType.isValidTimeZone`: `GMT`, or an id `TimeZone` resolves to another zone.
- **`long_value`** –

  `Number.longValue`: a `BigInteger` or `BigDecimal` wraps to 64 bits; a double saturates, NaN is 0.
- **`parse_big_decimal`** –

  `new BigDecimal(String)`: sign, digits with an optional point, an optional exponent; else None.
- **`parse_double`** –

  `Double.valueOf(String)`: trimmed; sign; decimal or hexadecimal; `NaN`; `Infinity`; a type suffix.
- **`parse_float`** –

  `Float.valueOf(String)`: as `parse_double`, rounded to Java's `float`.
- **`parse_long`** –

  `Long.valueOf(String)` and its kin: an optional sign and ASCII digits, or None.
- **`time_zone`** –

  `TimeZone.getTimeZone(id)`, or None for an id Java does not know (EVL-07, DD-042).
- **`to_big_integer`** –

  `AtlasBuiltInTypes.toBigInteger`: an integer as it is, a decimal or a double truncated toward zero.
- **`to_float32`** –

  Round a double to Java's `float` and hold it as the shortest decimal of the 32-bit value (DD-040).

Attributes:

- **`DOUBLE_MAX`** –

  `Double.MAX_VALUE`.
- **`DOUBLE_MIN`** –

  `Double.MIN_VALUE`, the smallest positive `double`.
- **`FLOAT_MAX`** –

  `Float.MAX_VALUE`, exactly, as a double.
- **`FLOAT_MIN`** –

  `Float.MIN_VALUE`, the smallest positive `float`, as a double.
- **`SHORT_ZONE_IDS`** –

  Java's legacy three-letter time zone ids that the tz database lacks, and the zones Java maps them to

### DOUBLE\_MAX

```
DOUBLE_MAX = 1.7976931348623157e+308
```

`Double.MAX_VALUE`.

### DOUBLE\_MIN

```
DOUBLE_MIN = 5e-324
```

`Double.MIN_VALUE`, the smallest positive `double`.

### FLOAT\_MAX

```
FLOAT_MAX = struct.unpack('<f', b'\xff\xff\x7f\x7f')[0]
```

`Float.MAX_VALUE`, exactly, as a double.

### FLOAT\_MIN

```
FLOAT_MIN = 1.401298464324817e-45
```

`Float.MIN_VALUE`, the smallest positive `float`, as a double.

### SHORT\_ZONE\_IDS

```
SHORT_ZONE_IDS = {
    "ACT": "Australia/Darwin",
    "AET": "Australia/Sydney",
    "AGT": "America/Argentina/Buenos_Aires",
    "ART": "Africa/Cairo",
    "AST": "America/Anchorage",
    "BET": "America/Sao_Paulo",
    "BST": "Asia/Dhaka",
    "CAT": "Africa/Harare",
    "CNT": "America/St_Johns",
    "CST": "America/Chicago",
    "CTT": "Asia/Shanghai",
    "EAT": "Africa/Addis_Ababa",
    "ECT": "Europe/Paris",
    "IET": "America/Indiana/Indianapolis",
    "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo",
    "MIT": "Pacific/Apia",
    "NET": "Asia/Yerevan",
    "NST": "Pacific/Auckland",
    "PLT": "Asia/Karachi",
    "PNT": "America/Phoenix",
    "PRT": "America/Puerto_Rico",
    "PST": "America/Los_Angeles",
    "SST": "Pacific/Guadalcanal",
    "VST": "Asia/Ho_Chi_Minh",
}
```

Java's legacy three-letter time zone ids that the tz database lacks, and the zones Java maps them to (`ZoneId.SHORT_IDS`).

### JavaNumber

```
JavaNumber = int | float | Decimal
```

### big\_decimal\_value\_of

```
big_decimal_value_of(value: float) -> Decimal
```

`BigDecimal.valueOf(double)`: the decimal of `Double.toString` (`5` becomes `5.0`).

### double\_value

```
double_value(value: JavaNumber) -> float
```

`Number.doubleValue`: the number as Java's `double` (an infinity beyond its range).

### float\_value

```
float_value(value: JavaNumber) -> float
```

`Number.floatValue`: the number as Java's `float` (an infinity beyond its range).

### is\_long

```
is_long(value: object) -> TypeGuard[int]
```

Whether `value` is an integer Jackson reads as an `Integer` or a `Long`, not a `BigInteger`.

### is\_number

```
is_number(value: object) -> TypeGuard[JavaNumber]
```

`value instanceof Number`: an `int`, `float` or `Decimal`, but not a `bool`.

### is\_valid\_time\_zone

```
is_valid_time_zone(zone_id: str) -> bool
```

`AtlasClassificationType.isValidTimeZone`: `GMT`, or an id `TimeZone` resolves to another zone.

### long\_value

```
long_value(value: JavaNumber) -> int
```

`Number.longValue`: a `BigInteger` or `BigDecimal` wraps to 64 bits; a double saturates, NaN is 0.

### parse\_big\_decimal

```
parse_big_decimal(text: str) -> Decimal | None
```

`new BigDecimal(String)`: sign, digits with an optional point, an optional exponent; else None.

### parse\_double

```
parse_double(text: str) -> float | None
```

`Double.valueOf(String)`: trimmed; sign; decimal or hexadecimal; `NaN`; `Infinity`; a type suffix.

### parse\_float

```
parse_float(text: str) -> float | None
```

`Float.valueOf(String)`: as `parse_double`, rounded to Java's `float`.

### parse\_long

```
parse_long(text: str) -> int | None
```

`Long.valueOf(String)` and its kin: an optional sign and ASCII digits, or None.

### time\_zone

```
time_zone(zone_id: str) -> tzinfo | None
```

`TimeZone.getTimeZone(id)`, or None for an id Java does not know (EVL-07, DD-042).

Java knows tz database zones, its legacy short ids and custom `GMT±h[h][[:]mm]` offsets, and answers any other id with `GMT`.

### to\_big\_integer

```
to_big_integer(value: JavaNumber) -> int
```

`AtlasBuiltInTypes.toBigInteger`: an integer as it is, a decimal or a double truncated toward zero.

Raises:

- `ValueError` –

  A NaN or infinite double, which `new BigDecimal(String)` rejects.

### to\_float32

```
to_float32(value: float) -> float
```

Round a double to Java's `float` and hold it as the shortest decimal of the 32-bit value (DD-040).

A value beyond `Float.MAX_VALUE` becomes an infinity, as Java's narrowing conversion does.

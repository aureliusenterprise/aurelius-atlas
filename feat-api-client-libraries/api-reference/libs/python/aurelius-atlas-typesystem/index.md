# aurelius-atlas-typesystem

The Atlas type system for Aurelius Atlas, without I/O ([DD-002](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)): the type registry and the types that type definitions resolve to. Since increment [1.2](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/conversion/increments/1-2-type-registry/index.md>): the built-in, array, map, enum and struct types, attribute types and constraints. Since [1.3](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/conversion/increments/1-3-type-hierarchies/index.md>): entity and classification hierarchies, relationship and business metadata types.

```
from aurelius_atlas_typesystem.registry import TypeRegistry

registry = TypeRegistry()
with registry.update() as transient:  # committed when the block ends, discarded when it raises
    transient.add_types(types_def)  # resolves every type; raises AtlasError on a bad reference
registry.entity_type("hive_table")
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

Atlas types: what a type definition becomes once its references are resolved (DD-025).

Ported from `org.apache.atlas.type` of Apache Atlas 2.4.0, the definition side only: the value side (validation, normalisation, defaults) arrives with entities in 2.1. A type resolves against a registry in three phases, as Java's `resolveReferences`, `resolveReferencesPhase2` and `resolveReferencesPhase3`.

Classes:

- **`ArrayType`** –

  `array<T>` with its cardinality and value counts (`AtlasArrayType`, TRG-02).
- **`AtlasAttribute`** –

  A resolved attribute of a struct-like type (`AtlasStructType.AtlasAttribute`).
- **`AtlasType`** –

  A type: its name, category and service type (`AtlasType`).
- **`BuiltInType`** –

  A primitive type such as `string` or `int` (`AtlasBuiltInTypes`, TRG-01).
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

  `objectid`: a reference to an entity of `object_type` (`AtlasObjectIdType`).
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

- **`type_for_attribute`** –

  This array, or a new one over the element's attribute type when that differs (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

This array, or a new one over the element's attribute type when that differs (TRG-11).

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

A type: its name, category and service type (`AtlasType`).

Methods:

- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

### BuiltInType

```
BuiltInType(type_name: str)
```

Bases: `AtlasType`

A primitive type such as `string` or `int` (`AtlasBuiltInTypes`, TRG-01).

Methods:

- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

### ClassificationType

```
ClassificationType(classification_def: AtlasClassificationDef)
```

Bases: `_HierarchyType`

A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07).

Methods:

- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`can_apply_to_entity_type`** –

  Whether the classification may be applied to `entity_type` (THY-07).
- **`is_sub_type_of`** –

  Whether `other` is among this type's super types, at any depth (THY-04).
- **`is_super_type_of`** –

  Whether `other` is among this type's sub types, at any depth (THY-04).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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
- **`super_types`** (`list[_HierarchyType]`) –
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
super_types: list[_HierarchyType] = []
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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

Bases: `_HierarchyType`

An entity type: its hierarchy, relationship and business attributes (THY-01 to THY-06, THY-10 to THY-12).

Methods:

- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`business_attribute`** –

  The attribute `attribute_name` of business metadata `metadata_name` on this type (THY-12).
- **`is_sub_type_of`** –

  Whether `other` is among this type's super types, at any depth (THY-04).
- **`is_super_type_of`** –

  Whether `other` is among this type's sub types, at any depth (THY-04).
- **`relationship_attribute`** –

  The relationship attribute `name` of `relationship_type`, else of the first relationship (THY-10).
- **`type_for_attribute`** –

  An attribute holds an entity as `objectid` of this entity type (TRG-11).

Attributes:

- **`all_attributes`** (`dict[str, AtlasAttribute]`) –
- **`all_sub_types`** (`list[str]`) –
- **`all_super_types`** (`list[str]`) –
- **`business_attributes`** (`dict[str, dict[str, BusinessAttribute]]`) –
- **`category`** –
- **`display_text_attribute`** –
- **`entity_def`** –
- **`header_attributes`** (`dict[str, AtlasAttribute]`) –
- **`is_internal`** –
- **`min_info_attributes`** (`dict[str, AtlasAttribute]`) –
- **`owned_ref_attributes`** (`list[AtlasAttribute]`) –
- **`relationship_attributes`** (`dict[str, dict[str, AtlasAttribute]]`) –
- **`service_type`** –
- **`struct_def`** –
- **`sub_types`** (`list[str]`) –
- **`super_types`** (`list[_HierarchyType]`) –
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
super_types: list[_HierarchyType] = []
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

### EnumType

```
EnumType(enum_def: AtlasEnumDef)
```

Bases: `AtlasType`

An enum type: its elements by value and ordinal, and its default (`AtlasEnumType`, TRG-14).

Methods:

- **`element`** –

  The element with `value`, compared without case, or None (TRG-14).
- **`element_by_ordinal`** –

  The element with `ordinal`, or None (TRG-14).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

### MapType

```
MapType(
    key_type_name: str, value_type_name: str, *, key_type: AtlasType | None = None, value_type: AtlasType | None = None
)
```

Bases: `AtlasType`

`map<K,V>` (`AtlasMapType`, TRG-02).

Methods:

- **`type_for_attribute`** –

  This map, or a new one over the key's and value's attribute types when they differ (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

This map, or a new one over the key's and value's attribute types when they differ (TRG-11).

### ObjectIdType

```
ObjectIdType(object_type: str | None = ATLAS_TYPE_ASSET)
```

Bases: `AtlasType`

`objectid`: a reference to an entity of `object_type` (`AtlasObjectIdType`).

Methods:

- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

### RelationshipType

```
RelationshipType(relationship_def: AtlasRelationshipDef)
```

Bases: `StructType`

A relationship type: its ends, label and the attributes it adds to them (THY-08 to THY-10).

Methods:

- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

### StructType

```
StructType(struct_def: AtlasStructDef)
```

Bases: `AtlasType`

A struct type, and the base of every type with attributes (`AtlasStructType`, TRG-10 to TRG-13).

Methods:

- **`attribute`** –

  The attribute named exactly `name`, then the system and business attribute, or None (TRG-13, THY-05).
- **`attribute_type`** –

  The type of the attribute named `name`, or None (TRG-13).
- **`type_for_attribute`** –

  The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

#### type\_for\_attribute

```
type_for_attribute() -> AtlasType
```

The type an attribute of this type holds; an entity type is held as an `objectid` (TRG-11).

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

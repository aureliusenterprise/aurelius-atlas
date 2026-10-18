# aurelius-atlas-core

Atlas stores and services for Aurelius Atlas ([DD-002](<https://aureliusenterprise.github.io/phase1-1.4-typedef-store/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)). Since increment [1.4](<https://aureliusenterprise.github.io/phase1-1.4-typedef-store/architecture/conversion/increments/1-4-typedef-store/index.md>): the typedef store, which keeps type definitions in one Elasticsearch document and serves them from the type registry.

```
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
```

## Installation

```
dependencies = ["aurelius-atlas-core"]

[tool.uv.sources.aurelius-atlas-core]
workspace = true
```

## Documentation

## aurelius\_atlas\_core.typedef\_store

The typedef store: type definitions kept in Elasticsearch and served from the registry (TDS-01 to TDS-13).

Ported from `AtlasTypeDefGraphStore` and its def stores (`Atlas*DefStoreV2`) of Apache Atlas 2.4.0. A change is tried on the registry's transient copy, checked as Atlas's def stores check it, written as one document (DD-028) and only then committed to the registry (TDS-10).

Type Aliases:

- **`TypeUsage`** –

  Whether entities, classifications or relationships of a type exist (DD-030).

Classes:

- **`TypedefStore`** –

  Type definitions kept in a `TypedefDocument`, served from a `TypeRegistry` (`AtlasTypeDefGraphStore`).

Functions:

- **`is_valid_name`** –

  A letter, then letters, digits, spaces or `_`; optionally after `__` (`isValidName`, TDS-02).
- **`never_in_use`** –

  The type usage until the entity store exists (2.2): no type is in use (DD-030).
- **`rectify`** –

  Repair what older stores allowed, as `rectifyTypeErrorsIfAny` does on load (TDS-12).
- **`referenced_type_names`** –

  The type names inside `array<…>` and `map<…,…>` (`AtlasTypeUtil.getReferencedTypeNames`, TDS-04).

Attributes:

- **`DEFAULT_REFRESH_SECONDS`** –

  How long a process answers from its registry before it checks for another process's change (DD-029).

### DEFAULT\_REFRESH\_SECONDS

```
DEFAULT_REFRESH_SECONDS = 5.0
```

How long a process answers from its registry before it checks for another process's change (DD-029).

### TypeUsage

```
TypeUsage = Callable[[str], Awaitable[bool]]
```

Whether entities, classifications or relationships of a type exist (DD-030).

### TypedefStore

```
TypedefStore(
    registry: TypeRegistry,
    document: TypedefDocument,
    *,
    usage: TypeUsage = never_in_use,
    refresh_seconds: float = DEFAULT_REFRESH_SECONDS,
    clock: Callable[[], float] = monotonic,
    now: Callable[[], datetime] = lambda: now(UTC),
)
```

Type definitions kept in a `TypedefDocument`, served from a `TypeRegistry` (`AtlasTypeDefGraphStore`).

Methods:

- **`create_types_def`** –

  Create the definitions, all or none (`createTypesDef`, TDS-01 to TDS-06, TDS-10).
- **`delete_type_by_name`** –

  Delete the definition named `name` (`deleteTypeByName`, TDS-09).
- **`delete_types_def`** –

  Delete the definitions found by GUID, else name, unless something refers to them (TDS-09, TDS-10).
- **`load`** –

  Prepare the document and load every stored definition into the registry (`init`, TDS-12).
- **`refresh`** –

  Reload when another process changed the definitions; checked at most every refresh interval (TDS-13).
- **`update_types_def`** –

  Update the definitions found by GUID, else name (`updateTypesDef`, TDS-07, TDS-08, TDS-10).

Attributes:

- **`registry`** –

#### registry

```
registry = registry
```

#### create\_types\_def

```
create_types_def(types_def: AtlasTypesDef, user: str | None = None) -> AtlasTypesDef
```

Create the definitions, all or none (`createTypesDef`, TDS-01 to TDS-06, TDS-10).

Returns:

- `AtlasTypesDef` –

  The created definitions, as stored.

Raises:

- `AtlasError` –

  A definition is invalid, exists already or refers to an unknown type.

#### delete\_type\_by\_name

```
delete_type_by_name(name: str) -> None
```

Delete the definition named `name` (`deleteTypeByName`, TDS-09).

Raises:

- `AtlasError` –

  `TYPE_NAME_INVALID` for a blank name, `TYPE_NAME_NOT_FOUND` for an unknown one and `SYSTEM_TYPE` for a built-in, array or map type.

#### delete\_types\_def

```
delete_types_def(types_def: AtlasTypesDef) -> None
```

Delete the definitions found by GUID, else name, unless something refers to them (TDS-09, TDS-10).

Raises:

- `AtlasError` –

  A definition is not found, is in use or is referred to.

#### load

```
load() -> None
```

Prepare the document and load every stored definition into the registry (`init`, TDS-12).

#### refresh

```
refresh(*, force: bool = False) -> bool
```

Reload when another process changed the definitions; checked at most every refresh interval (TDS-13).

Returns:

- `bool` –

  Whether the registry was reloaded.

#### update\_types\_def

```
update_types_def(types_def: AtlasTypesDef, user: str | None = None) -> AtlasTypesDef
```

Update the definitions found by GUID, else name (`updateTypesDef`, TDS-07, TDS-08, TDS-10).

Returns:

- `AtlasTypesDef` –

  The updated definitions, as stored.

Raises:

- `AtlasError` –

  A definition is not found, or changes what may not change.

### is\_valid\_name

```
is_valid_name(name: str | None) -> bool
```

A letter, then letters, digits, spaces or `_`; optionally after `__` (`isValidName`, TDS-02).

### never\_in\_use

```
never_in_use(_type_name: str) -> bool
```

The type usage until the entity store exists (2.2): no type is in use (DD-030).

### rectify

```
rectify(types_def: AtlasTypesDef) -> AtlasTypesDef
```

Repair what older stores allowed, as `rectifyTypeErrorsIfAny` does on load (TDS-12).

A second struct, classification or entity definition with the same name is dropped, and an `ownedRef` constraint on an attribute that refers to no entity type is removed.

### referenced\_type\_names

```
referenced_type_names(type_name: str | None) -> list[str]
```

The type names inside `array<…>` and `map<…,…>` (`AtlasTypeUtil.getReferencedTypeNames`, TDS-04).

## aurelius\_atlas\_core.typedef\_document

The stored type definitions: one Elasticsearch document, written with optimistic concurrency (DD-028, DD-029).

Classes:

- **`DocumentVersion`** –

  Which write of the document a reader saw: Elasticsearch's `_seq_no` and `_primary_term` (TDS-11).
- **`ElasticsearchTypedefDocument`** –

  The type definitions as one document of the `aurelius-atlas-typedefs` index (DD-028).
- **`TypedefDocument`** –

  Where the type definitions are kept.
- **`VersionConflictError`** –

  Another process wrote the document since this one read it (TDS-11).

Attributes:

- **`TYPEDEF_DOCUMENT_ID`** –

  The id of the one document that holds every type definition.
- **`TYPEDEF_INDEX`** –

  The alias of the index that holds the type definitions.

### TYPEDEF\_DOCUMENT\_ID

```
TYPEDEF_DOCUMENT_ID = 'typedefs'
```

The id of the one document that holds every type definition.

### TYPEDEF\_INDEX

```
TYPEDEF_INDEX = 'aurelius-atlas-typedefs'
```

The alias of the index that holds the type definitions.

### DocumentVersion

```
DocumentVersion(seq_no: int, primary_term: int)
```

Which write of the document a reader saw: Elasticsearch's `_seq_no` and `_primary_term` (TDS-11).

Attributes:

- **`primary_term`** (`int`) –
- **`seq_no`** (`int`) –

#### primary\_term

```
primary_term: int
```

#### seq\_no

```
seq_no: int
```

### ElasticsearchTypedefDocument

```
ElasticsearchTypedefDocument(client: AsyncElasticsearch, index: str = TYPEDEF_INDEX)
```

The type definitions as one document of the `aurelius-atlas-typedefs` index (DD-028).

Methods:

- **`prepare`** –

  Create the index behind the alias unless it exists; the document itself is not searched.
- **`read`** –

  The stored definitions and their version; `(None, None)` when nothing is stored (TDS-12).
- **`version`** –

  The version of the stored definitions, or None when nothing is stored (TDS-13).
- **`write`** –

  Replace the stored definitions if they are still at `expected`; create them when it is None (TDS-11).

#### prepare

```
prepare() -> None
```

Create the index behind the alias unless it exists; the document itself is not searched.

#### read

```
read() -> tuple[AtlasTypesDef | None, DocumentVersion | None]
```

The stored definitions and their version; `(None, None)` when nothing is stored (TDS-12).

#### version

```
version() -> DocumentVersion | None
```

The version of the stored definitions, or None when nothing is stored (TDS-13).

#### write

```
write(types_def: AtlasTypesDef, expected: DocumentVersion | None) -> DocumentVersion
```

Replace the stored definitions if they are still at `expected`; create them when it is None (TDS-11).

Raises:

- `VersionConflictError` –

  Another process wrote the document first.

### TypedefDocument

Bases: `Protocol`

Where the type definitions are kept.

Methods:

- **`prepare`** –

  Make sure the definitions can be read and written, such as by creating an index.
- **`read`** –

  The stored definitions and their version; `(None, None)` when nothing is stored.
- **`version`** –

  The version of the stored definitions, without reading them.
- **`write`** –

  Replace the stored definitions, if they are still at `expected`.

#### prepare

```
prepare() -> None
```

Make sure the definitions can be read and written, such as by creating an index.

#### read

```
read() -> tuple[AtlasTypesDef | None, DocumentVersion | None]
```

The stored definitions and their version; `(None, None)` when nothing is stored.

#### version

```
version() -> DocumentVersion | None
```

The version of the stored definitions, without reading them.

#### write

```
write(types_def: AtlasTypesDef, expected: DocumentVersion | None) -> DocumentVersion
```

Replace the stored definitions, if they are still at `expected`.

Raises:

- `VersionConflictError` –

  The stored definitions changed since `expected` was read.

### VersionConflictError

Bases: `Exception`

Another process wrote the document since this one read it (TDS-11).

## aurelius\_atlas\_core.stored\_form

What Atlas keeps of a type definition, and so answers with afterwards (TDS-03, TDS-05 to TDS-07).

Atlas's def stores write a definition to a graph vertex and build every response from the vertex again (`toEntityDef(vertex)`, …). Attributes go through the legacy form of `toJsonFromAttribute` and `toAttributeDefFromJson`; these functions apply the same round trip without the graph (DD-028).

Functions:

- **`java_end_string`** –

  `AtlasRelationshipEndDef.toString`, as `RELATIONSHIPDEF_INVALID_END*_UPDATE` messages show it (TDS-08).
- **`stamp_created`** –

  `createTypeVertex`: fill in what a new definition lacks (TDS-03); changes `typedef`, as Java does.
- **`stamp_updated`** –

  `updateTypeVertex` and `markVertexUpdated`: keep what may not change, bump the version (TDS-07).
- **`stored_attribute`** –

  An attribute after `toJsonFromAttribute` and `toAttributeDefFromJson` (TDS-05).
- **`stored_typedef`** –

  The definition as Atlas reads it back from its vertex (`to*Def(vertex)`, TDS-05, TDS-06).

Attributes:

- **`JAVA_INT_MAX`** –

  `Integer.MAX_VALUE`: the upper bound Atlas stores for an unbounded list or set.
- **`LEGACY_KIND`** –

  The legacy `DataTypes.TypeCategory` names Atlas's `TYPE_MATCH_FAILED` messages use (TDS-02).

### JAVA\_INT\_MAX

```
JAVA_INT_MAX = 2147483647
```

`Integer.MAX_VALUE`: the upper bound Atlas stores for an unbounded list or set.

### LEGACY\_KIND

```
LEGACY_KIND = {
    TypeCategory.ENUM: "ENUM",
    TypeCategory.STRUCT: "STRUCT",
    TypeCategory.CLASSIFICATION: "TRAIT",
    TypeCategory.ENTITY: "CLASS",
    TypeCategory.RELATIONSHIP: "RELATIONSHIP",
    TypeCategory.BUSINESS_METADATA: "BUSINESS_METADATA",
}
```

The legacy `DataTypes.TypeCategory` names Atlas's `TYPE_MATCH_FAILED` messages use (TDS-02).

### java\_end\_string

```
java_end_string(end: AtlasRelationshipEndDef | None) -> str
```

`AtlasRelationshipEndDef.toString`, as `RELATIONSHIPDEF_INVALID_END*_UPDATE` messages show it (TDS-08).

### stamp\_created

```
stamp_created(typedef: AtlasBaseTypeDef, now: datetime, user: str | None) -> None
```

`createTypeVertex`: fill in what a new definition lacks (TDS-03); changes `typedef`, as Java does.

### stamp\_updated

```
stamp_updated(typedef: AtlasBaseTypeDef, stored: AtlasBaseTypeDef, now: datetime, user: str | None) -> None
```

`updateTypeVertex` and `markVertexUpdated`: keep what may not change, bump the version (TDS-07).

### stored\_attribute

```
stored_attribute(attribute: AtlasAttribute) -> AtlasAttributeDef
```

An attribute after `toJsonFromAttribute` and `toAttributeDefFromJson` (TDS-05).

### stored\_typedef

```
stored_typedef(typedef: AtlasBaseTypeDef, type_: StructType | None) -> AtlasBaseTypeDef
```

The definition as Atlas reads it back from its vertex (`to*Def(vertex)`, TDS-05, TDS-06).

`type_` is the definition's resolved type, whose attributes are stored; None for an enum.

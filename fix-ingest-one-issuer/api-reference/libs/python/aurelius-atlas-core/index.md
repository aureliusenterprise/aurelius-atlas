# aurelius-atlas-core

Atlas stores and services for Aurelius Atlas ([DD-002](<https://aureliusenterprise.github.io/fix-ingest-one-issuer/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)). Since increment [1.4](<https://aureliusenterprise.github.io/fix-ingest-one-issuer/architecture/conversion/increments/1-4-typedef-store/index.md>): the typedef store, which keeps type definitions in one Elasticsearch document and serves them from the type registry. Since [1.5](<https://aureliusenterprise.github.io/fix-ingest-one-issuer/architecture/conversion/increments/1-5-builtin-models/index.md>): Apache Atlas's built-in models and their typedef patches, loaded at start-up.

```
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
await ModelLoader(store).load(BUILTIN_MODELS_DIR)  # addons/models of Atlas 2.4.0, and their patches
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

Ported from `AtlasTypeDefGraphStore` and its def stores (`Atlas*DefStoreV2`) of Apache Atlas 2.4.0. A change is tried on the registry's transient copy, checked as Atlas's def stores check it, written as one document (DD-028) and only then committed to the registry (TDS-10). The document also holds the record of each typedef patch, written with the patch's change (DD-031).

Type Aliases:

- **`TypeUsage`** –

  Whether entities, classifications or relationships of a type exist (DD-030).

Classes:

- **`PatchChange`** –

  What a typedef patch decided (MDL-07): its status, and the definitions it updates, if any.
- **`TypedefStore`** –

  Type definitions kept in a `TypedefDocument`, served from a `TypeRegistry` (`AtlasTypeDefGraphStore`).

Functions:

- **`is_newer_version`** –

  `ObjectUtils.compare(new, old) > 0`: compared as strings, an absent version less than any (MDL-02).
- **`is_valid_name`** –

  A letter, then letters, digits, spaces or `_`; optionally after `__` (`isValidName`, TDS-02).
- **`java_compare`** –

  Compare as Java's `String.compareTo` does: by UTF-16 code unit (MDL-01, MDL-02).
- **`never_in_use`** –

  The type usage until the entity store exists (2.2): no type is in use (DD-030).
- **`rectify`** –

  Repair what older stores allowed, as `rectifyTypeErrorsIfAny` does on load (TDS-12).
- **`referenced_type_names`** –

  The type names inside `array<…>` and `map<…,…>` (`AtlasTypeUtil.getReferencedTypeNames`, TDS-04).
- **`types_def_of`** –

  An `AtlasTypesDef` holding `typedefs`, each in the list of its kind.
- **`types_to_create`** –

  The definitions whose name is not registered, as any kind or built-in (`getTypesToCreate`, MDL-02).
- **`types_to_update`** –

  The definitions registered as the same kind, when newer (`getTypesToUpdate`, MDL-02).

Attributes:

- **`ADD_MANDATORY_ATTRIBUTE`** –

  The patch action under which an update may add mandatory attributes (`TYPEDEF_PATCH_ADD_MANDATORY_ATTRIBUTE`).
- **`DEFAULT_REFRESH_SECONDS`** –

  How long a process answers from its registry before it checks for another process's change (DD-029).

### ADD\_MANDATORY\_ATTRIBUTE

```
ADD_MANDATORY_ATTRIBUTE = 'ADD_MANDATORY_ATTRIBUTE'
```

The patch action under which an update may add mandatory attributes (`TYPEDEF_PATCH_ADD_MANDATORY_ATTRIBUTE`).

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

### PatchChange

```
PatchChange(status: PatchStatus, update: AtlasTypesDef | None = None, patching: str | None = None)
```

What a typedef patch decided (MDL-07): its status, and the definitions it updates, if any.

`patching` names the action when the update runs "in type patching" (`RequestContext.isInTypePatching`): attributes may then be removed, a relationship's category may change and its ends may swap, and under `ADD_MANDATORY_ATTRIBUTE` mandatory attributes may be added (MDL-10, MDL-11).

Attributes:

- **`patching`** (`str | None`) –
- **`status`** (`PatchStatus`) –
- **`update`** (`AtlasTypesDef | None`) –

#### patching

```
patching: str | None = None
```

#### status

```
status: PatchStatus
```

#### update

```
update: AtlasTypesDef | None = None
```

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

- **`apply_patch`** –

  Apply a typedef patch unless its record says it is done, and record how it ended (MDL-05, MDL-06).
- **`create_types_def`** –

  Create the definitions, all or none (`createTypesDef`, TDS-01 to TDS-06, TDS-10).
- **`create_update_types_def`** –

  Create the definitions not registered and update the registered ones, all or none (MDL-02, MDL-03).
- **`delete_type_by_name`** –

  Delete the definition named `name` (`deleteTypeByName`, TDS-09).
- **`delete_types_def`** –

  Delete the definitions found by GUID, else name, unless something refers to them (TDS-09, TDS-10).
- **`get_by_guid`** –

  The registered definition with `guid`, of any kind (`getByGuid`, TYR-02).
- **`get_by_name`** –

  The registered definition named `name`, of any kind (`getByName`, TYR-01).
- **`get_def_by_guid`** –

  The registered definition of `kind` with `guid` (`get{Kind}DefByGuid`, TYR-03).
- **`get_def_by_name`** –

  The registered definition of `kind` named `name` (`get{Kind}DefByName`, TYR-03).
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

#### apply\_patch

```
apply_patch(patch: AtlasPatch, decide: Callable[[TypeRegistry], PatchChange]) -> PatchStatus | None
```

Apply a typedef patch unless its record says it is done, and record how it ended (MDL-05, MDL-06).

`decide` looks at the registry and says what the patch does; an `AtlasError` from it, or from the update it asks for, makes the patch `FAILED`, and leaves the definitions as they were. Any other error is raised. The patch's record is written with its change (DD-031); a patch without an id is not recorded.

Returns:

- `PatchStatus | None` –

  How the patch ended, or None when its record says it was applied or skipped before.

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

#### create\_update\_types\_def

```
create_update_types_def(
    types_def: AtlasTypesDef, *, check_type_version: bool = False, user: str | None = None
) -> AtlasTypesDef
```

Create the definitions not registered and update the registered ones, all or none (MDL-02, MDL-03).

`createUpdateTypesDef`: what to create and update is decided on the newest stored definitions, and again after a conflict (DD-033). With `check_type_version`, as at start-up, only definitions with a greater `typeVersion` are updated. Nothing is written when there is nothing to create or update.

Returns:

- `AtlasTypesDef` –

  The created and updated definitions, as stored.

Raises:

- `AtlasError` –

  A definition is invalid or refers to an unknown type.

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

#### get\_by\_guid

```
get_by_guid(guid: str) -> AtlasBaseTypeDef
```

The registered definition with `guid`, of any kind (`getByGuid`, TYR-02).

Raises:

- `AtlasError` –

  `TYPE_GUID_NOT_FOUND` for a blank or unknown GUID.

#### get\_by\_name

```
get_by_name(name: str) -> AtlasBaseTypeDef
```

The registered definition named `name`, of any kind (`getByName`, TYR-01).

Raises:

- `AtlasError` –

  `TYPE_NAME_INVALID` for a blank name, `TYPE_NAME_NOT_FOUND` for an unknown one and `SYSTEM_TYPE` for a built-in, array or map type.

#### get\_def\_by\_guid

```
get_def_by_guid(kind: TypeCategory, guid: str) -> AtlasBaseTypeDef
```

The registered definition of `kind` with `guid` (`get{Kind}DefByGuid`, TYR-03).

Raises:

- `AtlasError` –

  `TYPE_GUID_NOT_FOUND` when no definition of `kind` has the GUID.

#### get\_def\_by\_name

```
get_def_by_name(kind: TypeCategory, name: str) -> AtlasBaseTypeDef
```

The registered definition of `kind` named `name` (`get{Kind}DefByName`, TYR-03).

Raises:

- `AtlasError` –

  `TYPE_NAME_NOT_FOUND` when no definition of `kind` has the name.

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

### is\_newer\_version

```
is_newer_version(new: str | None, old: str | None) -> bool
```

`ObjectUtils.compare(new, old) > 0`: compared as strings, an absent version less than any (MDL-02).

### is\_valid\_name

```
is_valid_name(name: str | None) -> bool
```

A letter, then letters, digits, spaces or `_`; optionally after `__` (`isValidName`, TDS-02).

### java\_compare

```
java_compare(left: str, right: str) -> int
```

Compare as Java's `String.compareTo` does: by UTF-16 code unit (MDL-01, MDL-02).

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

### types\_def\_of

```
types_def_of(typedefs: Iterable[AtlasBaseTypeDef]) -> AtlasTypesDef
```

An `AtlasTypesDef` holding `typedefs`, each in the list of its kind.

### types\_to\_create

```
types_to_create(types_def: AtlasTypesDef, registry: TypeRegistry) -> AtlasTypesDef
```

The definitions whose name is not registered, as any kind or built-in (`getTypesToCreate`, MDL-02).

### types\_to\_update

```
types_to_update(types_def: AtlasTypesDef, registry: TypeRegistry, *, check_type_version: bool) -> AtlasTypesDef
```

The definitions registered as the same kind, when newer (`getTypesToUpdate`, MDL-02).

With `check_type_version`, only those whose `typeVersion` is greater than the registered one. Each keeps the registered attributes, or an enum the registered elements, that it lacks.

## aurelius\_atlas\_core.model\_loader

Atlas's built-in models and their typedef patches, loaded at start-up (MDL-01 to MDL-15).

Ported from `AtlasTypeDefStoreInitializer` of Apache Atlas 2.4.0. Each model file and each patch is one change of the typedef store, decided on the newest stored definitions (DD-033); a patch's record is written with its change (DD-031).

Type Aliases:

- **`PatchHandler`** –

Classes:

- **`ModelLoad`** –

  What loading a models directory did: the files that failed, the patch files stopped, each patch's status.
- **`ModelLoader`** –

  Loads a models directory into a typedef store (`AtlasTypeDefStoreInitializer.loadBootstrapTypeDefs`).
- **`PatchDataError`** –

  Patch data that Atlas does not check, and fails on with a runtime exception (MDL-06, MDL-13).
- **`TypedefPatch`** –

  One typedef patch (`AtlasTypeDefStoreInitializer.TypeDefPatch`, MDL-05).
- **`TypedefPatches`** –

  A patch file (`TypeDefPatches`, MDL-05).

Functions:

- **`add_attribute`** –

  `ADD_ATTRIBUTE`: add attributes to an entity, classification, struct or relationship (MDL-09).
- **`add_mandatory_attribute`** –

  `ADD_MANDATORY_ATTRIBUTE`: add mandatory primitive attributes that have a default value (MDL-10).
- **`add_super_types`** –

  `ADD_SUPER_TYPES`: add super types to an entity type (MDL-14).
- **`is_patch_applicable`** –

  `isPatchApplicable`: no `typeVersion`, or `applyToVersion` ignoring case, or below it (MDL-07).
- **`load_plan`** –

  The model and patch files in the order they load, each with whether it is a patch file (MDL-01).
- **`remove_legacy_ref_attributes`** –

  `REMOVE_LEGACY_REF_ATTRIBUTES`: move a relationship's legacy attributes to the relationship (MDL-11).
- **`set_service_type`** –

  `SET_SERVICE_TYPE`: set a type's service type; without one, the update keeps the stored one (MDL-12).
- **`sorted_entries`** –

  The entries of `directory` by name, compared as `File.compareTo` does on Unix (MDL-01).
- **`update_attribute`** –

  `UPDATE_ATTRIBUTE`: replace or add attributes of an entity, classification or struct (MDL-09).
- **`update_attribute_metadata`** –

  `UPDATE_ATTRIBUTE_METADATA`: set the search weight or index type of an attribute (MDL-13).
- **`update_enum_def`** –

  `UPDATE_ENUMDEF`: add the elements to an enum (MDL-08).
- **`update_typedef_options`** –

  `UPDATE_TYPEDEF_OPTIONS`: merge options into a type's options (MDL-12).

Attributes:

- **`BUILTIN_MODELS_DIR`** –

  `addons/models` of Apache Atlas 2.4.0, unchanged (DD-032).
- **`LOGGER`** –
- **`PATCHES_FOLDER_NAME`** –

  The sub-directory of a models directory that holds its patches.
- **`PATCH_HANDLERS`** (`dict[str, PatchHandler]`) –

  The patch actions of Atlas 2.4.0 (`applyTypePatches`, MDL-07 to MDL-14).
- **`RACE_ATTEMPTS`** –

  How often a model file or patch is tried while another process keeps writing first (MDL-15, DD-036).
- **`REMOVE_LEGACY_REF_ATTRIBUTES`** –

  The patch action under which an update may remove attributes and swap a relationship's ends (MDL-11).

### BUILTIN\_MODELS\_DIR

```
BUILTIN_MODELS_DIR = Path(__file__).parent / 'models'
```

`addons/models` of Apache Atlas 2.4.0, unchanged (DD-032).

### LOGGER

```
LOGGER = logging.getLogger(__name__)
```

### PATCHES\_FOLDER\_NAME

```
PATCHES_FOLDER_NAME = 'patches'
```

The sub-directory of a models directory that holds its patches.

### PATCH\_HANDLERS

```
PATCH_HANDLERS: dict[str, PatchHandler] = {
    "UPDATE_ENUMDEF": update_enum_def,
    "ADD_ATTRIBUTE": add_attribute,
    "UPDATE_ATTRIBUTE": update_attribute,
    REMOVE_LEGACY_REF_ATTRIBUTES: remove_legacy_ref_attributes,
    "UPDATE_TYPEDEF_OPTIONS": update_typedef_options,
    "SET_SERVICE_TYPE": set_service_type,
    "UPDATE_ATTRIBUTE_METADATA": update_attribute_metadata,
    "ADD_SUPER_TYPES": add_super_types,
    ADD_MANDATORY_ATTRIBUTE: add_mandatory_attribute,
}
```

The patch actions of Atlas 2.4.0 (`applyTypePatches`, MDL-07 to MDL-14).

### RACE\_ATTEMPTS

```
RACE_ATTEMPTS = 10
```

How often a model file or patch is tried while another process keeps writing first (MDL-15, DD-036).

### REMOVE\_LEGACY\_REF\_ATTRIBUTES

```
REMOVE_LEGACY_REF_ATTRIBUTES = 'REMOVE_LEGACY_REF_ATTRIBUTES'
```

The patch action under which an update may remove attributes and swap a relationship's ends (MDL-11).

### PatchHandler

```
PatchHandler = Callable[[TypedefPatch, TypeRegistry], PatchChange]
```

### ModelLoad

```
ModelLoad(
    failed_files: list[Path] = list(),
    stopped_patch_files: list[Path] = list(),
    patches: dict[str, PatchStatus | None] = dict(),
)
```

What loading a models directory did: the files that failed, the patch files stopped, each patch's status.

Attributes:

- **`failed_files`** (`list[Path]`) –
- **`patches`** (`dict[str, PatchStatus | None]`) –
- **`stopped_patch_files`** (`list[Path]`) –

#### failed\_files

```
failed_files: list[Path] = field(default_factory=list)
```

#### patches

```
patches: dict[str, PatchStatus | None] = field(default_factory=dict)
```

#### stopped\_patch\_files

```
stopped_patch_files: list[Path] = field(default_factory=list)
```

### ModelLoader

```
ModelLoader(store: TypedefStore)
```

Loads a models directory into a typedef store (`AtlasTypeDefStoreInitializer.loadBootstrapTypeDefs`).

Methods:

- **`load`** –

  Load the model files and apply the patch files of `models_dir`, in the order of `load_plan` (MDL-01).

#### load

```
load(models_dir: Path) -> ModelLoad
```

Load the model files and apply the patch files of `models_dir`, in the order of `load_plan` (MDL-01).

Returns:

- `ModelLoad` –

  What failed, and how each patch ended.

### PatchDataError

Bases: `ValueError`

Patch data that Atlas does not check, and fails on with a runtime exception (MDL-06, MDL-13).

### TypedefPatch

Bases: `AtlasModel`

One typedef patch (`AtlasTypeDefStoreInitializer.TypeDefPatch`, MDL-05).

Methods:

- **`record`** –

  The patch's record, before its status is known.

Attributes:

- **`action`** (`str | None`) –
- **`apply_to_version`** (`str | None`) –
- **`attribute_defs`** (`list[AtlasAttributeDef] | None`) –
- **`attribute_name`** (`str | None`) –
- **`description`** (`str | None`) –
- **`element_defs`** (`list[AtlasEnumElementDef] | None`) –
- **`id`** (`str | None`) –
- **`params`** (`dict[str, Any] | None`) –
- **`service_type`** (`str | None`) –
- **`super_types`** (`list[str] | None`) –
- **`type_def_options`** (`dict[str, str] | None`) –
- **`type_name`** (`str | None`) –
- **`update_to_version`** (`str | None`) –

#### action

```
action: str | None = None
```

#### apply\_to\_version

```
apply_to_version: str | None = None
```

#### attribute\_defs

```
attribute_defs: list[AtlasAttributeDef] | None = None
```

#### attribute\_name

```
attribute_name: str | None = None
```

#### description

```
description: str | None = None
```

#### element\_defs

```
element_defs: list[AtlasEnumElementDef] | None = None
```

#### id

```
id: str | None = None
```

#### params

```
params: dict[str, Any] | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### super\_types

```
super_types: list[str] | None = None
```

#### type\_def\_options

```
type_def_options: dict[str, str] | None = None
```

#### type\_name

```
type_name: str | None = None
```

#### update\_to\_version

```
update_to_version: str | None = None
```

#### record

```
record() -> AtlasPatch
```

The patch's record, before its status is known.

### TypedefPatches

Bases: `AtlasModel`

A patch file (`TypeDefPatches`, MDL-05).

Attributes:

- **`patches`** (`list[TypedefPatch] | None`) –

#### patches

```
patches: list[TypedefPatch] | None = None
```

### add\_attribute

```
add_attribute(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`ADD_ATTRIBUTE`: add attributes to an entity, classification, struct or relationship (MDL-09).

### add\_mandatory\_attribute

```
add_mandatory_attribute(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`ADD_MANDATORY_ATTRIBUTE`: add mandatory primitive attributes that have a default value (MDL-10).

### add\_super\_types

```
add_super_types(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`ADD_SUPER_TYPES`: add super types to an entity type (MDL-14).

### is\_patch\_applicable

```
is_patch_applicable(patch: TypedefPatch, typedef: AtlasBaseTypeDef) -> bool
```

`isPatchApplicable`: no `typeVersion`, or `applyToVersion` ignoring case, or below it (MDL-07).

### load\_plan

```
load_plan(models_dir: Path) -> list[tuple[Path, bool]]
```

The model and patch files in the order they load, each with whether it is a patch file (MDL-01).

`loadBootstrapTypeDefs`:

each sub-directory except `patches` in name order, then the directory itself; of each, its files in name order, then the files of its `patches` sub-directory. A directory without entries contributes nothing.

### remove\_legacy\_ref\_attributes

```
remove_legacy_ref_attributes(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`REMOVE_LEGACY_REF_ATTRIBUTES`: move a relationship's legacy attributes to the relationship (MDL-11).

### set\_service\_type

```
set_service_type(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`SET_SERVICE_TYPE`: set a type's service type; without one, the update keeps the stored one (MDL-12).

### sorted\_entries

```
sorted_entries(directory: Path) -> list[Path]
```

The entries of `directory` by name, compared as `File.compareTo` does on Unix (MDL-01).

### update\_attribute

```
update_attribute(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`UPDATE_ATTRIBUTE`: replace or add attributes of an entity, classification or struct (MDL-09).

### update\_attribute\_metadata

```
update_attribute_metadata(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`UPDATE_ATTRIBUTE_METADATA`: set the search weight or index type of an attribute (MDL-13).

### update\_enum\_def

```
update_enum_def(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`UPDATE_ENUMDEF`: add the elements to an enum (MDL-08).

### update\_typedef\_options

```
update_typedef_options(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange
```

`UPDATE_TYPEDEF_OPTIONS`: merge options into a type's options (MDL-12).

## aurelius\_atlas\_core.typedef\_document

The stored type definitions: one Elasticsearch document, written with optimistic concurrency (DD-028, DD-029).

Classes:

- **`DocumentVersion`** –

  Which write of the document a reader saw: Elasticsearch's `_seq_no` and `_primary_term` (TDS-11).
- **`ElasticsearchTypedefDocument`** –

  The type definitions as one document of the `aurelius-atlas-typedefs` index (DD-028).
- **`StoredTypedefs`** –

  What the document holds: the definitions, and the record of each typedef patch (DD-028, DD-031).
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
read() -> tuple[StoredTypedefs | None, DocumentVersion | None]
```

The stored definitions and their version; `(None, None)` when nothing is stored (TDS-12).

#### version

```
version() -> DocumentVersion | None
```

The version of the stored definitions, or None when nothing is stored (TDS-13).

#### write

```
write(stored: StoredTypedefs, expected: DocumentVersion | None) -> DocumentVersion
```

Replace the stored definitions if they are still at `expected`; create them when it is None (TDS-11).

Raises:

- `VersionConflictError` –

  Another process wrote the document first.

### StoredTypedefs

```
StoredTypedefs(types_def: AtlasTypesDef, patches: list[AtlasPatch] = list())
```

What the document holds: the definitions, and the record of each typedef patch (DD-028, DD-031).

Methods:

- **`from_json`** –

  Read a document's source; one written before 1.5 has no `patches`.
- **`to_json`** –

  The document's source: `typesDef` and `patches`.

Attributes:

- **`patches`** (`list[AtlasPatch]`) –
- **`types_def`** (`AtlasTypesDef`) –

#### patches

```
patches: list[AtlasPatch] = field(default_factory=list)
```

#### types\_def

```
types_def: AtlasTypesDef
```

#### from\_json

```
from_json(source: dict[str, Any]) -> StoredTypedefs
```

Read a document's source; one written before 1.5 has no `patches`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The document's source: `typesDef` and `patches`.

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
read() -> tuple[StoredTypedefs | None, DocumentVersion | None]
```

The stored definitions and their version; `(None, None)` when nothing is stored.

#### version

```
version() -> DocumentVersion | None
```

The version of the stored definitions, without reading them.

#### write

```
write(stored: StoredTypedefs, expected: DocumentVersion | None) -> DocumentVersion
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

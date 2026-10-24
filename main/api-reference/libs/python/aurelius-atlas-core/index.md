# aurelius-atlas-core

Atlas stores and services for Aurelius Atlas ([DD-002](<https://aureliusenterprise.github.io/main/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)). Since increment [1.4](<https://aureliusenterprise.github.io/main/architecture/conversion/increments/1-4-typedef-store/index.md>): the typedef store, which keeps type definitions in one Elasticsearch document and serves them from the type registry. Since [1.5](<https://aureliusenterprise.github.io/main/architecture/conversion/increments/1-5-builtin-models/index.md>): Apache Atlas's built-in models and their typedef patches, loaded at start-up. Since [1.6](<https://aureliusenterprise.github.io/main/architecture/conversion/increments/1-6-types-rest/index.md>): the store's reads and the search of `/v2/types/typedefs`. Since [2.2](<https://aureliusenterprise.github.io/main/architecture/conversion/increments/2-2-entity-store/index.md>): the entity store, which keeps each entity as one Elasticsearch document, reserves unique attribute values and writes several entities all or nothing through a journal (DD-043 to DD-048).

```
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
await ModelLoader(store).load(BUILTIN_MODELS_DIR)  # addons/models of Atlas 2.4.0, and their patches
store.get_by_name("hive_table")  # the registered definition, as resolution completed it
search_types_def(store.registry, TypeSearchFilter.from_query([("type", "ENTITY")]))  # each kind sorted by name
```

## Installation

```
dependencies = ["aurelius-atlas-core"]

[tool.uv.sources.aurelius-atlas-core]
workspace = true
```

## Vendored models

`aurelius_atlas_core/models/` is `addons/models` of Apache Atlas `release-2.4.0`, byte for byte ([DD-032](<https://aureliusenterprise.github.io/main/architecture/conversion/design-log/#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory>)). To prove it, compare it with the tag:

```
diff -r <apache-atlas checkout at release-2.4.0>/addons/models libs/python/aurelius-atlas-core/aurelius_atlas_core/models
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
- **`patches`** –

  The patch records, sorted by id as Java compares strings (`AtlasPatchRegistry.getAllPatches`, ENS-10).
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

#### patches

```
patches() -> list[AtlasPatch]
```

The patch records, sorted by id as Java compares strings (`AtlasPatchRegistry.getAllPatches`, ENS-10).

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

## aurelius\_atlas\_core.entity\_store

`EntityStore`: entities by GUID and unique attributes, written all or nothing (ENS-02 to ENS-09).

The storage side of `AtlasEntityStoreV2` and `EntityGraphMapper`: what a graph transaction gave Atlas, rebuilt on Elasticsearch with reserved unique values, conditional writes and a journal (DD-044 to DD-048).

Classes:

- **`ClassificationChange`** –

  One classification instance of a write: its new state and the version it was read in, or None for a new one.
- **`EntityChange`** –

  One entity of a write: its new state, and the version it was read in, or None for a new entity.
- **`EntityStore`** –

  Entities of the registry's entity types, and the relationships between them, in `EntityDocuments`.
- **`EntityVersionConflictError`** –

  Another write changed an entity after it was read (ENS-08); nothing was written.
- **`EntityWriteError`** –

  An entity could not be written for another reason; the write was undone (ENS-07).
- **`RelationshipChange`** –

  One relationship of a write: its new state and the version it was read in, or None for a new one.
- **`TaskChange`** –

  One task of a write: its new state and the version it was read in, or None for a new one (DD-079).
- **`UniqueValueTakenError`** –

  A write needs a unique value another entity holds (ENS-05); nothing was written.

Attributes:

- **`LEASE_MILLISECONDS`** –

  How long a write may take before recovery may undo it (DD-046).
- **`LEASE_PASSED_ERROR`** –
- **`REMOVE_UNREAD_ERROR`** –
- **`UNIQUE_VALUE_TAKEN_ERROR`** –
- **`UNKNOWN_ENTITY_TYPE_ERROR`** –
- **`VERSION_CONFLICT_ERROR`** –
- **`WRITE_FAILED_ERROR`** –

### LEASE\_MILLISECONDS

```
LEASE_MILLISECONDS = 60000
```

How long a write may take before recovery may undo it (DD-046).

### LEASE\_PASSED\_ERROR

```
LEASE_PASSED_ERROR = 'write {write_id} took longer than its lease'
```

### REMOVE\_UNREAD\_ERROR

```
REMOVE_UNREAD_ERROR = 'entity {guid} cannot be removed without the version it was read in'
```

### UNIQUE\_VALUE\_TAKEN\_ERROR

```
UNIQUE_VALUE_TAKEN_ERROR = 'unique value {attribute}={value} of type {type} is held by entity {holder}'
```

### UNKNOWN\_ENTITY\_TYPE\_ERROR

```
UNKNOWN_ENTITY_TYPE_ERROR = '{type} is not an entity type'
```

### VERSION\_CONFLICT\_ERROR

```
VERSION_CONFLICT_ERROR = 'entity {guid} was changed by another write'
```

### WRITE\_FAILED\_ERROR

```
WRITE_FAILED_ERROR = 'entity {guid} could not be written'
```

### ClassificationChange

```
ClassificationChange(
    classification: StoredClassification, expected: DocumentVersion | None = None, remove: bool = False
)
```

One classification instance of a write: its new state and the version it was read in, or None for a new one.

With `remove`, the write removes the instance, which must have been read (DD-071).

Attributes:

- **`classification`** (`StoredClassification`) –
- **`expected`** (`DocumentVersion | None`) –
- **`remove`** (`bool`) –

#### classification

```
classification: StoredClassification
```

#### expected

```
expected: DocumentVersion | None = None
```

#### remove

```
remove: bool = False
```

### EntityChange

```
EntityChange(entity: StoredEntity, expected: DocumentVersion | None = None, remove: bool = False)
```

One entity of a write: its new state, and the version it was read in, or None for a new entity.

With `remove`, the write removes the entity, which must have been read: `entity` is its state then (DD-056).

Attributes:

- **`entity`** (`StoredEntity`) –
- **`expected`** (`DocumentVersion | None`) –
- **`remove`** (`bool`) –

#### entity

```
entity: StoredEntity
```

#### expected

```
expected: DocumentVersion | None = None
```

#### remove

```
remove: bool = False
```

### EntityStore

```
EntityStore(
    registry: TypeRegistry,
    documents: EntityDocuments,
    *,
    clock: Callable[[], float] = time,
    new_id: Callable[[], str] = lambda: str(uuid4()),
)
```

Entities of the registry's entity types, and the relationships between them, in `EntityDocuments`.

Methods:

- **`classifications_of_types`** –

  The classification instances of these types, or of every type for None (DD-090).
- **`classified`** –

  The entities listing any of these classification instances, attached or propagated (DD-075, DD-076).
- **`find_by_unique_attributes`** –

  The `ACTIVE` entity of the type, else of its first sub type, holding every given unique value (ENS-06).
- **`get`** –

  The entity with `guid` as last written, or None (ENS-04).
- **`get_classifications`** –

  The classification instances with these GUIDs that exist, as last written (CLS-02, DD-070).
- **`get_many`** –

  The entities with these GUIDs that exist (ENS-04).
- **`get_relationships`** –

  The relationships with these GUIDs that exist, as last written (REL-06, DD-061).
- **`get_tasks`** –

  The tasks with these GUIDs that exist, as last written (TSK-06, DD-079).
- **`list_tasks`** –

  Every task, or those `PENDING` or `IN_PROGRESS`, oldest first (TSK-04, TSK-06).
- **`new_guid`** –

  A new entity's GUID: a random UUID in canonical lower-case text (ENS-02, DD-044).
- **`now`** –

  The current time in epoch milliseconds, as Atlas stores times.
- **`prepare`** –

  Create the indices that are missing (ENS-01).
- **`recover`** –

  Finish or undo the writes whose lease has passed; the number of entries handled (ENS-07, DD-046).
- **`referring`** –

  The entities whose references name any of these GUIDs (EDL-10, DD-057).
- **`search`** –

  The entities of a search query's page, how many match it in all, and their scores (DD-089).
- **`type_in_use`** –

  Whether an entity, relationship or classification of exactly this type exists, in any state.
- **`write`** –

  Write new, changed and removed entities and the documents they list, all or nothing, through the journal.

Attributes:

- **`registry`** –
- **`task_listeners`** (`list[Callable[[], None]]`) –

  Called after a write that recorded tasks, to wake a worker (DD-080).

#### registry

```
registry = registry
```

#### task\_listeners

```
task_listeners: list[Callable[[], None]] = []
```

Called after a write that recorded tasks, to wake a worker (DD-080).

#### classifications\_of\_types

```
classifications_of_types(type_names: Collection[str] | None) -> list[StoredClassification]
```

The classification instances of these types, or of every type for None (DD-090).

#### classified

```
classified(guids: Sequence[str]) -> list[VersionedEntity]
```

The entities listing any of these classification instances, attached or propagated (DD-075, DD-076).

#### find\_by\_unique\_attributes

```
find_by_unique_attributes(entity_type: EntityType, values: Mapping[str, Any]) -> VersionedEntity | None
```

The `ACTIVE` entity of the type, else of its first sub type, holding every given unique value (ENS-06).

Values are normalised by the attribute's type; values of other attributes and nulls are ignored.

#### get

```
get(guid: str) -> VersionedEntity | None
```

The entity with `guid` as last written, or None (ENS-04).

#### get\_classifications

```
get_classifications(guids: Sequence[str]) -> dict[str, VersionedClassification]
```

The classification instances with these GUIDs that exist, as last written (CLS-02, DD-070).

#### get\_many

```
get_many(guids: Sequence[str]) -> dict[str, VersionedEntity]
```

The entities with these GUIDs that exist (ENS-04).

#### get\_relationships

```
get_relationships(guids: Sequence[str]) -> dict[str, VersionedRelationship]
```

The relationships with these GUIDs that exist, as last written (REL-06, DD-061).

#### get\_tasks

```
get_tasks(guids: Sequence[str]) -> dict[str, tuple[StoredTask, DocumentVersion]]
```

The tasks with these GUIDs that exist, as last written (TSK-06, DD-079).

#### list\_tasks

```
list_tasks(*, open_only: bool = False) -> list[tuple[StoredTask, DocumentVersion]]
```

Every task, or those `PENDING` or `IN_PROGRESS`, oldest first (TSK-04, TSK-06).

#### new\_guid

```
new_guid() -> str
```

A new entity's GUID: a random UUID in canonical lower-case text (ENS-02, DD-044).

#### now

```
now() -> int
```

The current time in epoch milliseconds, as Atlas stores times.

#### prepare

```
prepare() -> None
```

Create the indices that are missing (ENS-01).

#### recover

```
recover() -> int
```

Finish or undo the writes whose lease has passed; the number of entries handled (ENS-07, DD-046).

A committed write only releases what it no longer holds; any other is undone: an entity is restored only while it carries the write's id, a reservation released only while the write holds it.

#### referring

```
referring(guids: Sequence[str]) -> list[VersionedEntity]
```

The entities whose references name any of these GUIDs (EDL-10, DD-057).

#### search

```
search(query: SearchQuery) -> SearchHits
```

The entities of a search query's page, how many match it in all, and their scores (DD-089).

#### type\_in\_use

```
type_in_use(type_name: str) -> bool
```

Whether an entity, relationship or classification of exactly this type exists, in any state.

ENS-09, REL-10, CLS-12, DD-048.

The typedef store's check.

#### write

```
write(
    changes: Sequence[EntityChange],
    relationship_changes: Sequence[RelationshipChange] = (),
    classification_changes: Sequence[ClassificationChange] = (),
    task_changes: Sequence[TaskChange] = (),
) -> None
```

Write new, changed and removed entities and the documents they list, all or nothing, through the journal.

ENS-05, ENS-07, ENS-08. Each written entity carries the GUIDs its references name (DD-057); removals, relationships and classification instances are journaled too (DD-056, DD-062, DD-071).

Raises:

- `UniqueValueTakenError` –

  A unique value is held by another entity.
- `EntityVersionConflictError` –

  An entity changed since it was read.
- `EntityWriteError` –

  An entity could not be written; the write was undone.

### EntityVersionConflictError

```
EntityVersionConflictError(guid: str)
```

Bases: `Exception`

Another write changed an entity after it was read (ENS-08); nothing was written.

Attributes:

- **`guid`** –

#### guid

```
guid = guid
```

### EntityWriteError

Bases: `Exception`

An entity could not be written for another reason; the write was undone (ENS-07).

### RelationshipChange

```
RelationshipChange(relationship: StoredRelationship, expected: DocumentVersion | None = None, remove: bool = False)
```

One relationship of a write: its new state and the version it was read in, or None for a new one.

With `remove`, the write removes the relationship, which must have been read (DD-062).

Attributes:

- **`expected`** (`DocumentVersion | None`) –
- **`relationship`** (`StoredRelationship`) –
- **`remove`** (`bool`) –

#### expected

```
expected: DocumentVersion | None = None
```

#### relationship

```
relationship: StoredRelationship
```

#### remove

```
remove: bool = False
```

### TaskChange

```
TaskChange(task: StoredTask, expected: DocumentVersion | None = None, remove: bool = False)
```

One task of a write: its new state and the version it was read in, or None for a new one (DD-079).

With `remove`, the write removes the task, which must have been read.

Attributes:

- **`expected`** (`DocumentVersion | None`) –
- **`remove`** (`bool`) –
- **`task`** (`StoredTask`) –

#### expected

```
expected: DocumentVersion | None = None
```

#### remove

```
remove: bool = False
```

#### task

```
task: StoredTask
```

### UniqueValueTakenError

```
UniqueValueTakenError(key: UniqueKey, holder: str)
```

Bases: `Exception`

A write needs a unique value another entity holds (ENS-05); nothing was written.

Attributes:

- **`holder`** –
- **`key`** –

#### holder

```
holder = holder
```

#### key

```
key = key
```

## aurelius\_atlas\_core.entity\_documents

The entities' documents in Elasticsearch: entities, unique value reservations and the write journal (ENS-01).

The I/O behind `EntityStore`: reads in real time, conditional writes, create-only reservations (DD-043 to DD-047). Documents go to Elasticsearch as the bytes of Atlas's JSON codec, so values keep their digits (DD-039).

Type Aliases:

- **`Linked`** –

  A document an entity lists: a relationship or a classification instance.

Classes:

- **`ElasticsearchEntityDocuments`** –

  `EntityDocuments` in three Elasticsearch indices behind aliases (DD-043, DD-045, DD-046).
- **`EntityDocuments`** –

  Where `EntityStore` keeps entities, reservations and its journal.
- **`JournalEntry`** –

  A write in flight: its id, lease, the entities' states before it, its reservations, releases and removals.
- **`LinkedKind`** –

  The documents an entity lists besides itself, each in an index of its own (DD-061, DD-070).
- **`LinkedWrite`** –

  What a write does to the documents of one `LinkedKind`: written ones at a version or new, removed ones.
- **`Reservation`** –

  A unique value held by an entity: the key's id, the holder's GUID and the write that reserved it (DD-045).
- **`VersionedClassification`** –

  A stored classification instance and the version it was read in (DD-047, DD-070).
- **`VersionedEntity`** –

  A stored entity and the version it was read in (DD-047).
- **`VersionedRelationship`** –

  A stored relationship and the version it was read in (DD-047, DD-061).
- **`WriteResult`** –

  How one entity of a bulk write ended: written, or failed by a version conflict or another error.

Attributes:

- **`CLASSIFICATION_INDEX`** –

  The alias of the classification index (DD-070).
- **`CLASSIFICATION_MAPPING`** (`dict[str, Any]`) –

  Classification instances by type and entity; attribute values stored, not indexed (DD-070).
- **`CLASSIFICATION_PAGE`** –

  How many classification instances one search page holds.
- **`ENTITY_FIELD_LIMIT`** –

  `index.mapping.total_fields.limit` of the entity index: a field per searchable attribute (DD-088).
- **`ENTITY_INDEX`** –

  The alias of the entity index (DD-043).
- **`ENTITY_MAPPING`** (`dict[str, Any]`) –

  System properties and referenced GUIDs mapped for exact lookup; attribute values stored, not indexed, and searched
- **`INDEX_PREFIX`** –

  The prefix of the three aliases; tests give their own.
- **`JOURNAL_INDEX`** –

  The alias of the write journal (DD-046).
- **`JOURNAL_PAGE`** –

  How many journal entries recovery reads at once; a live journal holds one entry per write in flight.
- **`KEYWORD_LIMIT`** –

  `ignore_above` of keyword search fields: the longest value a keyword holds, in characters (DD-092).
- **`LINKED_MODELS`** (`dict[LinkedKind, type[StoredRelationship | StoredClassification | StoredTask]]`) –
- **`REFERRING_PAGE`** –

  How many referring entities one search page holds (DD-057).
- **`RELATIONSHIP_INDEX`** –

  The alias of the relationship index (DD-061).
- **`RELATIONSHIP_MAPPING`** (`dict[str, Any]`) –

  Relationships by type, label, ends and state; attribute values stored, not indexed (DD-061).
- **`TASK_MAPPING`** (`dict[str, Any]`) –

  Tasks by status and creation time; parameters stored, not indexed (DD-079).
- **`TASK_PAGE`** –

  How many tasks one search page holds.
- **`UNIQUE_VALUE_INDEX`** –

  The alias of the unique value reservations (DD-045).

### CLASSIFICATION\_INDEX

```
CLASSIFICATION_INDEX = f'{INDEX_PREFIX}-classifications'
```

The alias of the classification index (DD-070).

### CLASSIFICATION\_MAPPING

```
CLASSIFICATION_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "typeName": _KEYWORD,
        "superTypeNames": _KEYWORD,
        "entityGuid": _KEYWORD,
        "entityStatus": _KEYWORD,
        "writeId": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
    },
}
```

Classification instances by type and entity; attribute values stored, not indexed (DD-070).

### CLASSIFICATION\_PAGE

```
CLASSIFICATION_PAGE = 1000
```

How many classification instances one search page holds.

### ENTITY\_FIELD\_LIMIT

```
ENTITY_FIELD_LIMIT = 100000
```

`index.mapping.total_fields.limit` of the entity index: a field per searchable attribute (DD-088).

### ENTITY\_INDEX

```
ENTITY_INDEX = f'{INDEX_PREFIX}-entities'
```

The alias of the entity index (DD-043).

### ENTITY\_MAPPING

```
ENTITY_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "typeName": _KEYWORD,
        "superTypeNames": _KEYWORD,
        "state": _KEYWORD,
        "createTime": {"type": "long"},
        "updateTime": {"type": "long"},
        "createdBy": _KEYWORD,
        "updatedBy": _KEYWORD,
        "version": {"type": "long"},
        "isIncomplete": {"type": "boolean"},
        "isProxy": {"type": "boolean"},
        "provenanceType": {"type": "integer"},
        "homeId": _KEYWORD,
        "labels": _KEYWORD,
        "writeId": _KEYWORD,
        "references": _KEYWORD,
        "relationshipGuids": _KEYWORD,
        "classificationGuids": _KEYWORD,
        "pendingTasks": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
        "customAttributes": {"type": "object", "dynamic": False},
        "search": {"type": "object", "dynamic": True, "subobjects": False},
    },
    "dynamic_templates": [
        {f"search_{kind}": {"path_match": f"search.{kind}.*", "mapping": _search_mapping(kind)}} for kind in KINDS
    ],
}
```

System properties and referenced GUIDs mapped for exact lookup; attribute values stored, not indexed, and searched in the typed fields of `search`, which the dynamic templates map by their kind (DD-043, DD-057, DD-088).

### INDEX\_PREFIX

```
INDEX_PREFIX = 'aurelius-atlas'
```

The prefix of the three aliases; tests give their own.

### JOURNAL\_INDEX

```
JOURNAL_INDEX = f'{INDEX_PREFIX}-entity-journal'
```

The alias of the write journal (DD-046).

### JOURNAL\_PAGE

```
JOURNAL_PAGE = 1000
```

How many journal entries recovery reads at once; a live journal holds one entry per write in flight.

### KEYWORD\_LIMIT

```
KEYWORD_LIMIT = 8191
```

`ignore_above` of keyword search fields: the longest value a keyword holds, in characters (DD-092).

### LINKED\_MODELS

```
LINKED_MODELS: dict[LinkedKind, type[StoredRelationship | StoredClassification | StoredTask]] = {
    LinkedKind.RELATIONSHIP: StoredRelationship,
    LinkedKind.CLASSIFICATION: StoredClassification,
    LinkedKind.TASK: StoredTask,
}
```

### REFERRING\_PAGE

```
REFERRING_PAGE = 1000
```

How many referring entities one search page holds (DD-057).

### RELATIONSHIP\_INDEX

```
RELATIONSHIP_INDEX = f'{INDEX_PREFIX}-relationships'
```

The alias of the relationship index (DD-061).

### RELATIONSHIP\_MAPPING

```
RELATIONSHIP_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "typeName": _KEYWORD,
        "label": _KEYWORD,
        "end1Guid": _KEYWORD,
        "end2Guid": _KEYWORD,
        "state": _KEYWORD,
        "writeId": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
    },
}
```

Relationships by type, label, ends and state; attribute values stored, not indexed (DD-061).

### TASK\_MAPPING

```
TASK_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "type": _KEYWORD,
        "status": _KEYWORD,
        "createdTime": {"type": "long"},
        "claimedUntil": {"type": "long"},
        "writeId": _KEYWORD,
    },
}
```

Tasks by status and creation time; parameters stored, not indexed (DD-079).

### TASK\_PAGE

```
TASK_PAGE = 1000
```

How many tasks one search page holds.

### UNIQUE\_VALUE\_INDEX

```
UNIQUE_VALUE_INDEX = f'{INDEX_PREFIX}-unique-values'
```

The alias of the unique value reservations (DD-045).

### Linked

```
Linked = StoredRelationship | StoredClassification | StoredTask
```

A document an entity lists: a relationship or a classification instance.

### ElasticsearchEntityDocuments

```
ElasticsearchEntityDocuments(client: AsyncElasticsearch, prefix: str = INDEX_PREFIX)
```

`EntityDocuments` in three Elasticsearch indices behind aliases (DD-043, DD-045, DD-046).

Methods:

- **`classifications_of_types`** –

  Refresh the classification index, then page through the instances of the types by GUID (DD-090).
- **`classified`** –

  Refresh the entity index, then page through the entities whose `classificationGuids` hold one (DD-076).
- **`count_linked_type`** –

  Refresh the kind's index, then count its documents of the type (REL-10, CLS-12).
- **`count_type`** –

  Refresh the entity index, then count the entities of the type (DD-048).
- **`delete_journal`** –

  Delete the entry; one already gone is fine.
- **`get`** –

  `mget` of the entity index: real time, as a get by id is (ENS-04).
- **`get_linked`** –

  `mget` of the kind's index: real time (DD-061, DD-070).
- **`journal`** –

  The entries of the journal, refreshed first so none written a moment ago is missed.
- **`list_tasks`** –

  Refresh the task index, then page through its tasks by creation time (TSK-04, TSK-06).
- **`prepare`** –

  Create each index behind its alias unless it exists (ENS-01).
- **`put_journal`** –

  Index the entry under its write id.
- **`referring`** –

  Refresh the entity index, then page through the entities whose `references` hold a GUID (DD-057).
- **`release`** –

  Delete the reservation when `guid` still holds it, guarded by its version.
- **`reservations`** –

  `mget` of the reservations, in real time.
- **`reserve`** –

  `op_type=create`: of two processes reserving one value, one fails (DD-045).
- **`restore`** –

  Index the state before, or delete an entity that did not exist before (DD-046).
- **`restore_linked`** –

  Index the document's state before, or delete one that did not exist before (DD-062).
- **`search`** –

  Refresh the entity index, then answer the query as a `bool` query of the search fields (DD-089).
- **`write`** –

  One bulk request over the indices: `create` a new document, `index` or `delete` with `if_seq_no`.

Attributes:

- **`aliases`** (`tuple[str, ...]`) –

  The aliases of the entity index, the reservations, the journal and the linked documents' indices.

#### aliases

```
aliases: tuple[str, ...]
```

The aliases of the entity index, the reservations, the journal and the linked documents' indices.

#### classifications\_of\_types

```
classifications_of_types(type_names: Collection[str] | None) -> list[StoredClassification]
```

Refresh the classification index, then page through the instances of the types by GUID (DD-090).

#### classified

```
classified(guids: Sequence[str]) -> list[VersionedEntity]
```

Refresh the entity index, then page through the entities whose `classificationGuids` hold one (DD-076).

#### count\_linked\_type

```
count_linked_type(kind: LinkedKind, type_name: str) -> int
```

Refresh the kind's index, then count its documents of the type (REL-10, CLS-12).

#### count\_type

```
count_type(type_name: str) -> int
```

Refresh the entity index, then count the entities of the type (DD-048).

#### delete\_journal

```
delete_journal(write_id: str) -> None
```

Delete the entry; one already gone is fine.

#### get

```
get(guids: Sequence[str]) -> dict[str, VersionedEntity]
```

`mget` of the entity index: real time, as a get by id is (ENS-04).

#### get\_linked

```
get_linked(kind: LinkedKind, guids: Sequence[str]) -> dict[str, tuple[Linked, DocumentVersion]]
```

`mget` of the kind's index: real time (DD-061, DD-070).

#### journal

```
journal() -> list[JournalEntry]
```

The entries of the journal, refreshed first so none written a moment ago is missed.

#### list\_tasks

```
list_tasks(*, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]
```

Refresh the task index, then page through its tasks by creation time (TSK-04, TSK-06).

#### prepare

```
prepare() -> None
```

Create each index behind its alias unless it exists (ENS-01).

An existing entity index gets the fields it lacks mapped, as `references` (EDL-10); mapped ones stay.

#### put\_journal

```
put_journal(entry: JournalEntry) -> None
```

Index the entry under its write id.

#### referring

```
referring(guids: Sequence[str]) -> list[VersionedEntity]
```

Refresh the entity index, then page through the entities whose `references` hold a GUID (DD-057).

#### release

```
release(key: str, guid: str) -> None
```

Delete the reservation when `guid` still holds it, guarded by its version.

#### reservations

```
reservations(keys: Sequence[str]) -> dict[str, Reservation]
```

`mget` of the reservations, in real time.

#### reserve

```
reserve(reservation: Reservation) -> Reservation | None
```

`op_type=create`: of two processes reserving one value, one fails (DD-045).

#### restore

```
restore(guid: str, before: StoredEntity | None) -> None
```

Index the state before, or delete an entity that did not exist before (DD-046).

#### restore\_linked

```
restore_linked(kind: LinkedKind, guid: str, before: Linked | None) -> None
```

Index the document's state before, or delete one that did not exist before (DD-062).

#### search

```
search(query: SearchQuery) -> SearchHits
```

Refresh the entity index, then answer the query as a `bool` query of the search fields (DD-089).

Free text is a scored `simple_query_string` over the text sub-fields (DD-092).

#### write

```
write(
    items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
    removed: Sequence[tuple[str, DocumentVersion]] = (),
    linked: Mapping[LinkedKind, LinkedWrite] | None = None,
) -> list[WriteResult]
```

One bulk request over the indices: `create` a new document, `index` or `delete` with `if_seq_no`.

DD-047, DD-056, DD-062, DD-071.

### EntityDocuments

Bases: `Protocol`

Where `EntityStore` keeps entities, reservations and its journal.

Methods:

- **`classifications_of_types`** –

  The classification instances of these types, or of every type for None, as of now (DD-090).
- **`classified`** –

  The entities listing any of these classification instances, as of now (DD-076).
- **`count_linked_type`** –

  How many documents of the kind and type exist, in any state, as of now (REL-10, CLS-12).
- **`count_type`** –

  How many entities of exactly this type exist, in any state, as of now.
- **`delete_journal`** –

  Delete a journal entry.
- **`get`** –

  The stored entities with these GUIDs, in real time; unknown GUIDs are left out.
- **`get_linked`** –

  The stored documents of a kind with these GUIDs, in real time; unknown GUIDs are left out (DD-061).
- **`journal`** –

  Every journal entry.
- **`list_tasks`** –

  Every task, or those `PENDING` or `IN_PROGRESS`, oldest first, as of now (TSK-04, TSK-06).
- **`prepare`** –

  Create the indices that are missing.
- **`put_journal`** –

  Write a journal entry.
- **`referring`** –

  The entities whose references name any of these GUIDs, as of now (DD-057).
- **`release`** –

  Delete the reservation of `key` if `guid` holds it.
- **`reservations`** –

  The reservations of these keys that exist.
- **`reserve`** –

  Make a reservation, create-only; the one holding the key when it is taken.
- **`restore`** –

  Put back an entity's state before a write, or delete one the write created.
- **`restore_linked`** –

  Put back a linked document's state before a write, or delete one the write created (DD-062).
- **`search`** –

  The entities of the query's page, as of now, how many match it in all, and their scores (DD-089).
- **`write`** –

  Write and remove entities and linked documents, new (no version) or at the version given.

#### classifications\_of\_types

```
classifications_of_types(type_names: Collection[str] | None) -> list[StoredClassification]
```

The classification instances of these types, or of every type for None, as of now (DD-090).

#### classified

```
classified(guids: Sequence[str]) -> list[VersionedEntity]
```

The entities listing any of these classification instances, as of now (DD-076).

#### count\_linked\_type

```
count_linked_type(kind: LinkedKind, type_name: str) -> int
```

How many documents of the kind and type exist, in any state, as of now (REL-10, CLS-12).

#### count\_type

```
count_type(type_name: str) -> int
```

How many entities of exactly this type exist, in any state, as of now.

#### delete\_journal

```
delete_journal(write_id: str) -> None
```

Delete a journal entry.

#### get

```
get(guids: Sequence[str]) -> dict[str, VersionedEntity]
```

The stored entities with these GUIDs, in real time; unknown GUIDs are left out.

#### get\_linked

```
get_linked(kind: LinkedKind, guids: Sequence[str]) -> dict[str, tuple[Linked, DocumentVersion]]
```

The stored documents of a kind with these GUIDs, in real time; unknown GUIDs are left out (DD-061).

#### journal

```
journal() -> list[JournalEntry]
```

Every journal entry.

#### list\_tasks

```
list_tasks(*, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]
```

Every task, or those `PENDING` or `IN_PROGRESS`, oldest first, as of now (TSK-04, TSK-06).

#### prepare

```
prepare() -> None
```

Create the indices that are missing.

#### put\_journal

```
put_journal(entry: JournalEntry) -> None
```

Write a journal entry.

#### referring

```
referring(guids: Sequence[str]) -> list[VersionedEntity]
```

The entities whose references name any of these GUIDs, as of now (DD-057).

#### release

```
release(key: str, guid: str) -> None
```

Delete the reservation of `key` if `guid` holds it.

#### reservations

```
reservations(keys: Sequence[str]) -> dict[str, Reservation]
```

The reservations of these keys that exist.

#### reserve

```
reserve(reservation: Reservation) -> Reservation | None
```

Make a reservation, create-only; the one holding the key when it is taken.

#### restore

```
restore(guid: str, before: StoredEntity | None) -> None
```

Put back an entity's state before a write, or delete one the write created.

#### restore\_linked

```
restore_linked(kind: LinkedKind, guid: str, before: Linked | None) -> None
```

Put back a linked document's state before a write, or delete one the write created (DD-062).

#### search

```
search(query: SearchQuery) -> SearchHits
```

The entities of the query's page, as of now, how many match it in all, and their scores (DD-089).

#### write

```
write(
    items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
    removed: Sequence[tuple[str, DocumentVersion]] = (),
    linked: Mapping[LinkedKind, LinkedWrite] | None = None,
) -> list[WriteResult]
```

Write and remove entities and linked documents, new (no version) or at the version given.

One bulk request; the results are in order: entities written, removed, then each kind's written, removed (DD-056, DD-062, DD-071).

### JournalEntry

Bases: `AtlasModel`

A write in flight: its id, lease, the entities' states before it, its reservations, releases and removals.

DD-046, DD-056.

Methods:

- **`before_entity`** –

  The state of `guid` before the write, or None for an entity the write created.
- **`before_linked`** –

  The state of a linked document before the write, or None for one the write created (DD-062, DD-071).

Attributes:

- **`before`** (`dict[str, dict[str, Any] | None]`) –
- **`committed`** (`bool`) –
- **`lease_until`** (`int`) –
- **`linked_before`** (`dict[str, dict[str, dict[str, Any] | None]]`) –
- **`released`** (`list[str]`) –
- **`removed`** (`list[str]`) –
- **`removed_linked`** (`dict[str, list[str]]`) –
- **`reserved`** (`list[str]`) –
- **`write_id`** (`str`) –

#### before

```
before: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
```

#### committed

```
committed: bool = False
```

#### lease\_until

```
lease_until: int
```

#### linked\_before

```
linked_before: dict[str, dict[str, dict[str, Any] | None]] = Field(default_factory=dict)
```

#### released

```
released: list[str] = Field(default_factory=list)
```

#### removed

```
removed: list[str] = Field(default_factory=list)
```

#### removed\_linked

```
removed_linked: dict[str, list[str]] = Field(default_factory=dict)
```

#### reserved

```
reserved: list[str] = Field(default_factory=list)
```

#### write\_id

```
write_id: str
```

#### before\_entity

```
before_entity(guid: str) -> StoredEntity | None
```

The state of `guid` before the write, or None for an entity the write created.

#### before\_linked

```
before_linked(kind: LinkedKind, guid: str) -> Linked | None
```

The state of a linked document before the write, or None for one the write created (DD-062, DD-071).

### LinkedKind

Bases: `StrEnum`

The documents an entity lists besides itself, each in an index of its own (DD-061, DD-070).

Attributes:

- **`CLASSIFICATION`** –
- **`RELATIONSHIP`** –
- **`TASK`** –

#### CLASSIFICATION

```
CLASSIFICATION = 'classifications'
```

#### RELATIONSHIP

```
RELATIONSHIP = 'relationships'
```

#### TASK

```
TASK = 'tasks'
```

### LinkedWrite

```
LinkedWrite(
    written: Sequence[tuple[Linked, DocumentVersion | None]] = (), removed: Sequence[tuple[str, DocumentVersion]] = ()
)
```

What a write does to the documents of one `LinkedKind`: written ones at a version or new, removed ones.

Attributes:

- **`removed`** (`Sequence[tuple[str, DocumentVersion]]`) –
- **`written`** (`Sequence[tuple[Linked, DocumentVersion | None]]`) –

#### removed

```
removed: Sequence[tuple[str, DocumentVersion]] = ()
```

#### written

```
written: Sequence[tuple[Linked, DocumentVersion | None]] = ()
```

### Reservation

```
Reservation(key: str, guid: str, write_id: str)
```

A unique value held by an entity: the key's id, the holder's GUID and the write that reserved it (DD-045).

Attributes:

- **`guid`** (`str`) –
- **`key`** (`str`) –
- **`write_id`** (`str`) –

#### guid

```
guid: str
```

#### key

```
key: str
```

#### write\_id

```
write_id: str
```

### VersionedClassification

```
VersionedClassification(classification: StoredClassification, version: DocumentVersion)
```

A stored classification instance and the version it was read in (DD-047, DD-070).

Attributes:

- **`classification`** (`StoredClassification`) –
- **`version`** (`DocumentVersion`) –

#### classification

```
classification: StoredClassification
```

#### version

```
version: DocumentVersion
```

### VersionedEntity

```
VersionedEntity(entity: StoredEntity, version: DocumentVersion)
```

A stored entity and the version it was read in (DD-047).

Attributes:

- **`entity`** (`StoredEntity`) –
- **`version`** (`DocumentVersion`) –

#### entity

```
entity: StoredEntity
```

#### version

```
version: DocumentVersion
```

### VersionedRelationship

```
VersionedRelationship(relationship: StoredRelationship, version: DocumentVersion | None)
```

A stored relationship and the version it was read in (DD-047, DD-061).

None for one a write request creates and has not written yet (DD-068).

Attributes:

- **`relationship`** (`StoredRelationship`) –
- **`version`** (`DocumentVersion | None`) –

#### relationship

```
relationship: StoredRelationship
```

#### version

```
version: DocumentVersion | None
```

### WriteResult

```
WriteResult(guid: str, written: bool, conflict: bool = False, kind: LinkedKind | None = None)
```

How one entity of a bulk write ended: written, or failed by a version conflict or another error.

Attributes:

- **`conflict`** (`bool`) –
- **`guid`** (`str`) –
- **`kind`** (`LinkedKind | None`) –
- **`written`** (`bool`) –

#### conflict

```
conflict: bool = False
```

#### guid

```
guid: str
```

#### kind

```
kind: LinkedKind | None = None
```

#### written

```
written: bool
```

## aurelius\_atlas\_core.stored\_entity

`StoredEntity`: an entity as stored, its system properties and its attribute values (ENS-03, DD-043).

What `EntityGraphMapper` and `GraphHelper` keep on an entity's vertex: the GUID, type and super type names, state, times, users, version and the attribute values, here under their qualified names.

Classes:

- **`StoredEntity`** –

  One document of the entity index; `write_id` names the write that last wrote it (DD-046).

Functions:

- **`stored_attributes`** –

  Attribute values keyed by qualified name; names the type does not have are left out (DD-043).

### StoredEntity

Bases: `AtlasModel`

One document of the entity index; `write_id` names the write that last wrote it (DD-046).

Methods:

- **`listing`** –

  This entity listing relationship `relationship_guid` as one it is an end of (DD-061).
- **`of`** –

  A new entity as stored (`createVertexWithGuid`): `ACTIVE`, both times `now`, `version` its own.
- **`reference_guids`** –

  The GUIDs this entity's references name, each once (EDL-10, DD-057).
- **`to_entity`** –

  The entity with its system properties and the stored attribute values by attribute name (ERD-03).
- **`touched`** –

  This entity, changed at `now` by `user` (`updateModificationMetadata`).
- **`unique_keys`** –

  The unique values this entity holds: those of its unique attributes with a value, while `ACTIVE`.
- **`unlisting`** –

  This entity no longer listing these relationships (DD-061).

Attributes:

- **`attributes`** (`dict[str, Any]`) –
- **`classification_guids`** (`list[str] | None`) –
- **`create_time`** (`int`) –
- **`created_by`** (`str | None`) –
- **`custom_attributes`** (`dict[str, str] | None`) –
- **`guid`** (`str`) –
- **`home_id`** (`str | None`) –
- **`is_incomplete`** (`bool`) –
- **`is_proxy`** (`bool | None`) –
- **`labels`** (`list[str] | None`) –
- **`pending_tasks`** (`list[str] | None`) –
- **`provenance_type`** (`int`) –
- **`references`** (`list[str] | None`) –
- **`relationship_guids`** (`list[str] | None`) –
- **`search`** (`dict[str, Any] | None`) –

  The search fields, written by the store (DD-088).
- **`state`** (`EntityStatus`) –
- **`super_type_names`** (`list[str]`) –
- **`type_name`** (`str`) –
- **`update_time`** (`int`) –
- **`updated_by`** (`str | None`) –
- **`version`** (`int`) –
- **`write_id`** (`str | None`) –

#### attributes

```
attributes: dict[str, Any] = Field(default_factory=dict)
```

#### classification\_guids

```
classification_guids: list[str] | None = None
```

#### create\_time

```
create_time: int = 0
```

#### created\_by

```
created_by: str | None = None
```

#### custom\_attributes

```
custom_attributes: dict[str, str] | None = None
```

#### guid

```
guid: str
```

#### home\_id

```
home_id: str | None = None
```

#### is\_incomplete

```
is_incomplete: bool = False
```

#### is\_proxy

```
is_proxy: bool | None = None
```

#### labels

```
labels: list[str] | None = None
```

#### pending\_tasks

```
pending_tasks: list[str] | None = None
```

#### provenance\_type

```
provenance_type: int = 0
```

#### references

```
references: list[str] | None = None
```

#### relationship\_guids

```
relationship_guids: list[str] | None = None
```

#### search

```
search: dict[str, Any] | None = None
```

The search fields, written by the store (DD-088).

#### state

```
state: EntityStatus = EntityStatus.ACTIVE
```

#### super\_type\_names

```
super_type_names: list[str] = Field(default_factory=list)
```

#### type\_name

```
type_name: str
```

#### update\_time

```
update_time: int = 0
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int = 0
```

#### write\_id

```
write_id: str | None = None
```

#### listing

```
listing(relationship_guid: str) -> Self
```

This entity listing relationship `relationship_guid` as one it is an end of (DD-061).

#### of

```
of(entity: AtlasEntity, entity_type: EntityType, *, guid: str, now: int, user: str | None) -> Self
```

A new entity as stored (`createVertexWithGuid`): `ACTIVE`, both times `now`, `version` its own.

Attributes the type does not have are left out; the others are stored under their qualified names.

#### reference\_guids

```
reference_guids(entity_type: EntityType) -> list[str]
```

The GUIDs this entity's references name, each once (EDL-10, DD-057).

Its own object id attributes and the elements and values of its arrays and maps of object ids; not soft references, nor references in structs, which Atlas keeps as properties rather than edges.

#### to\_entity

```
to_entity(entity_type: EntityType) -> AtlasEntity
```

The entity with its system properties and the stored attribute values by attribute name (ERD-03).

`labels` is a list even when empty, as Java's `getLabels` returns a set; `EntityRetriever` reads the attribute values as Atlas answers them.

#### touched

```
touched(*, now: int, user: str | None) -> Self
```

This entity, changed at `now` by `user` (`updateModificationMetadata`).

#### unique\_keys

```
unique_keys(entity_type: EntityType) -> list[UniqueKey]
```

The unique values this entity holds: those of its unique attributes with a value, while `ACTIVE`.

#### unlisting

```
unlisting(relationship_guids: set[str]) -> Self
```

This entity no longer listing these relationships (DD-061).

### stored\_attributes

```
stored_attributes(attributes: dict[str, Any], entity_type: EntityType) -> dict[str, Any]
```

Attribute values keyed by qualified name; names the type does not have are left out (DD-043).

## aurelius\_atlas\_core.unique\_key

`UniqueKey`: one unique attribute value of one entity type, the id of its reservation (ENS-05, DD-045).

Classes:

- **`UniqueKey`** –

  A value of a unique attribute of an entity type: what Atlas's `PER_TYPE_UNIQUE` index keeps once.

### UniqueKey

```
UniqueKey(type_name: str, attribute: str, value: Any)
```

A value of a unique attribute of an entity type: what Atlas's `PER_TYPE_UNIQUE` index keeps once.

`attribute` is the attribute's qualified name (`Referenceable.qualifiedName`), `value` the normalised value.

Attributes:

- **`attribute`** (`str`) –
- **`id`** (`str`) –

  The reservation's document id: a SHA-256 of type, attribute and value as the codec writes them.
- **`type_name`** (`str`) –
- **`value`** (`Any`) –

#### attribute

```
attribute: str
```

#### id

```
id: str
```

The reservation's document id: a SHA-256 of type, attribute and value as the codec writes them.

#### type\_name

```
type_name: str
```

#### value

```
value: Any
```

## aurelius\_atlas\_core.type\_search

Searching the registered type definitions with a filter of query parameters (TYR-05 to TYR-08).

Ported from `TypesREST.getSearchFilter`, `SearchFilter` and `FilterUtil` of Apache Atlas 2.4.0, and `AtlasTypeDefGraphStore.searchTypesDef`.

Classes:

- **`TypeSearchFilter`** –

  The parameters of a type search, each with its values in order (`SearchFilter`).

Functions:

- **`search_types_def`** –

  The registered definitions the filter keeps, each kind sorted by name (`searchTypesDef`, TYR-05, DD-034).
- **`type_def_headers`** –

  The header of each definition, enums first (`AtlasTypeUtil.toTypeDefHeader`, TYR-08).

Attributes:

- **`EXCLUDE_INTERNAL`** –

  The parameter that hides `__internal` and its sub types, compared without case (TYR-07).
- **`PARAM_NAME`** –
- **`PARAM_NOT_NAME`** –

  The filter's parameter names (`SearchFilter.PARAM_*`), compared with case.
- **`PARAM_NOT_SERVICETYPE`** –
- **`PARAM_NOT_SUPERTYPE`** –
- **`PARAM_SERVICETYPE`** –
- **`PARAM_SUPERTYPE`** –
- **`PARAM_TYPE`** –
- **`TYPE_NAME_INTERNAL`** –

  The super type of Atlas's internal entity types (`Constants.TYPE_NAME_INTERNAL`).

### EXCLUDE\_INTERNAL

```
EXCLUDE_INTERNAL = 'excludeInternalTypesAndReferences'
```

The parameter that hides `__internal` and its sub types, compared without case (TYR-07).

### PARAM\_NAME

```
PARAM_NAME = 'name'
```

### PARAM\_NOT\_NAME

```
PARAM_NOT_NAME = 'notname'
```

The filter's parameter names (`SearchFilter.PARAM_*`), compared with case.

### PARAM\_NOT\_SERVICETYPE

```
PARAM_NOT_SERVICETYPE = 'notservicetype'
```

### PARAM\_NOT\_SUPERTYPE

```
PARAM_NOT_SUPERTYPE = 'notsupertype'
```

### PARAM\_SERVICETYPE

```
PARAM_SERVICETYPE = 'servicetype'
```

### PARAM\_SUPERTYPE

```
PARAM_SUPERTYPE = 'supertype'
```

### PARAM\_TYPE

```
PARAM_TYPE = 'type'
```

### TYPE\_NAME\_INTERNAL

```
TYPE_NAME_INTERNAL = '__internal'
```

The super type of Atlas's internal entity types (`Constants.TYPE_NAME_INTERNAL`).

### TypeSearchFilter

```
TypeSearchFilter(params: dict[str, list[str]] = dict())
```

The parameters of a type search, each with its values in order (`SearchFilter`).

Methods:

- **`from_query`** –

  The filter of a request's query parameters (`getSearchFilter`, TYR-06, TYR-07).
- **`matches`** –

  Whether the filter keeps `type_` (`FilterUtil.getPredicateFromSearchFilter`, TYR-06).
- **`param`** –

  The first value of parameter `name` (`getParam`).

Attributes:

- **`params`** (`dict[str, list[str]]`) –

#### params

```
params: dict[str, list[str]] = field(default_factory=dict)
```

#### from\_query

```
from_query(items: Iterable[tuple[str, str]]) -> TypeSearchFilter
```

The filter of a request's query parameters (`getSearchFilter`, TYR-06, TYR-07).

Each parameter counts with its first value, in the order the parameters first appear; `excludeInternalTypesAndReferences=true` adds `notname` and `notsupertype` `__internal`.

#### matches

```
matches(type_: AtlasType) -> bool
```

Whether the filter keeps `type_` (`FilterUtil.getPredicateFromSearchFilter`, TYR-06).

#### param

```
param(name: str) -> str | None
```

The first value of parameter `name` (`getParam`).

### search\_types\_def

```
search_types_def(registry: TypeRegistry, search_filter: TypeSearchFilter) -> AtlasTypesDef
```

The registered definitions the filter keeps, each kind sorted by name (`searchTypesDef`, TYR-05, DD-034).

### type\_def\_headers

```
type_def_headers(types_def: AtlasTypesDef) -> list[AtlasTypeDefHeader]
```

The header of each definition, enums first (`AtlasTypeUtil.toTypeDefHeader`, TYR-08).

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

  One typedef patch of a models-directory patch file (MDL-05).
- **`TypedefPatches`** –

  A patch file: the patches of a models directory (MDL-05).

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

One typedef patch of a models-directory patch file (MDL-05).

The fields a patch uses depend on its `action`; the patch handlers read the ones their action needs.

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
action: str | None = Field(
    default=None,
    description="The action the patch performs, e.g. ``ADD_ATTRIBUTE`` or ``REMOVE_LEGACY_REF_ATTRIBUTES``.",
)
```

#### apply\_to\_version

```
apply_to_version: str | None = Field(
    default=None,
    description="The type version the patch applies to; a patch applies when the stored version equals it or starts below it.",
)
```

#### attribute\_defs

```
attribute_defs: list[AtlasAttributeDef] | None = Field(
    default=None, description="The attributes the patch adds to or changes on the type."
)
```

#### attribute\_name

```
attribute_name: str | None = Field(default=None, description='The name of a single attribute the patch acts on.')
```

#### description

```
description: str | None = Field(default=None, description='A description of the patch.')
```

#### element\_defs

```
element_defs: list[AtlasEnumElementDef] | None = Field(
    default=None, description="The enum values the patch adds to the type."
)
```

#### id

```
id: str | None = Field(default=None, description='The unique id of the patch.')
```

#### params

```
params: dict[str, Any] | None = Field(
    default=None,
    description="Parameters of the action, e.g. ``ownedAttribute``/``inverseAttribute`` for a ref-attribute patch.",
)
```

#### service\_type

```
service_type: str | None = Field(default=None, description='The service type of the patched type.')
```

#### super\_types

```
super_types: list[str] | None = Field(default=None, description='The super types the patch adds to the type.')
```

#### type\_def\_options

```
type_def_options: dict[str, str] | None = Field(
    default=None, description="The type options the patch sets on the type."
)
```

#### type\_name

```
type_name: str | None = Field(default=None, description='The name of the type the patch changes.')
```

#### update\_to\_version

```
update_to_version: str | None = Field(
    default=None, description="The type version the type gets when the patch is applied."
)
```

#### record

```
record() -> AtlasPatch
```

The patch's record, before its status is known.

### TypedefPatches

Bases: `AtlasModel`

A patch file: the patches of a models directory (MDL-05).

Attributes:

- **`patches`** (`list[TypedefPatch] | None`) –

#### patches

```
patches: list[TypedefPatch] | None = Field(
    default=None, description="The patches of the file, in the order they are applied."
)
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

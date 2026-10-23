# 1.2 Type registry

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-023, DD-024, DD-025; relies on DD-002, DD-020

## Scope

The registry that turns type definitions into resolved types, in a new library without I/O, `libs/python/aurelius-atlas-typesystem` (package `aurelius_atlas_typesystem`, [DD-002](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)):

- the registry: the built-in types, lookup by name and GUID, the definitions per kind, and updates made on a transient copy that is committed or discarded;
- the types: built-in, array, map, enum and struct, and for classification, entity, relationship and business metadata definitions their own attributes, resolved as a struct's are;
- attribute resolution: attribute types, cardinality, the classification and business metadata ban, and the `ownedRef` and `inverseRef` constraints;
- the Atlas error codes these raise, in the model library, where every layer can raise them ([DD-023](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/conversion/design-log/#dd-023-atlas-errors-live-in-the-model-library>)).

No endpoint changes; the server does not use the registry yet.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Super and sub types, inherited attributes, root types, classification `entityTypes` | 1.3 |
| Relationship ends and relationship attributes; business metadata `applicableEntityTypes` | 1.3 |
| Rejecting duplicate or reserved type names, and type names already in use | 1.4 (the store) |
| Validating, normalising and defaulting attribute values | 2.1 (DD-025) |
| JanusGraph property names, index field names and index-query escaping | dropped (DD-025) |

## Semantics

| Id | Rule |
| --- | --- |
| TRG-01 | A new registry holds the built-in types `boolean`, `byte`, `short`, `int`, `long`, `float`, `double`, `biginteger`, `bigdecimal`, `date` and `string` (category `PRIMITIVE`) and `objectid` (`OBJECT_ID_TYPE`), all with service type `atlas_core` |
| TRG-02 | A registered name answers its type. An unregistered `array<T>` or `map<K,V>` name is built on demand from its element, key and value types, splitting a map's at its first comma; an array built so has cardinality `LIST` and no element counts |
| TRG-03 | An unknown type name fails with `TYPE_NAME_NOT_FOUND` (404) and an unknown GUID with `TYPE_GUID_NOT_FOUND` (404), each naming what was asked for |
| TRG-04 | Definitions are found by name and by GUID, per kind and across all kinds; each kind lists its definitions, names and types, and the registry lists all type names, all types and all service types |
| TRG-05 | The registry changes only through a transient copy taken under the update lock. Committing makes the copy's types the registry's; releasing without committing discards them. The lock is re-entrant; waiting longer than its timeout fails with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` (500) ([DD-024](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/conversion/design-log/#dd-024-the-registry-is-updated-on-a-transient-copy-under-a-re-entrant-lock>)) |
| TRG-06 | Adding a definition registers it by name and, when it has one, by GUID. A later definition with the same name replaces the earlier one, a built-in type included |
| TRG-07 | Updating replaces the definition with the given GUID or name; a definition updated without a target is found by its GUID, else by its name, else ignored |
| TRG-08 | Removing by GUID or by name removes the definition under both. Removing the definitions of an `AtlasTypesDef` removes each by its GUID when it has one, else by its name. The transient copy records what was added, updated and removed, in order |
| TRG-09 | After every change the copy resolves every type again; the first failure is raised and nothing reaches the registry |
| TRG-10 | Each attribute's type must resolve. `LIST` and `SET` cardinality need an array type, else `INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY` (400); the array then takes the attribute's cardinality and value counts. An attribute whose type, array element or map value is a classification or business metadata type fails with `ATTRIBUTE_TYPE_INVALID` (400) |
| TRG-11 | An attribute's qualified name is `Type.attribute`, or its name when that contains a dot. An entity type in an attribute becomes `objectid` of that entity type, also inside arrays and maps; such an array or map is a new one, so an array keeps cardinality `LIST` and no value counts, as in Java. The attribute is an object reference when its type, array element or map value is `objectid` |
| TRG-12 | `ownedRef` needs an entity type (or an array or map of one), else `CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE`. `inverseRef` needs one too (`CONSTRAINT_INVERSE_REF_ATTRIBUTE_INVALID_TYPE`), a non-blank `attribute` parameter (`CONSTRAINT_MISSING_PARAMS`), that attribute defined on the referenced entity type (`CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING`) and of an entity type (`CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_INVALID_TYPE`), all 400; the inverse attribute is then linked |
| TRG-13 | A type's attributes are looked up by exact name; its unique attributes are those whose definition is unique |
| TRG-14 | An enum type finds its elements by value without case and by ordinal; its default is the definition's `defaultValue`, else the first element's value |
| TRG-15 | Every error carries Atlas's HTTP status, error code and message, with `{0}`, `{1}`, … filled in from its parameters in order |
| TRG-16 | Classification, entity, relationship and business metadata types resolve their own attributes as a struct type does |

TRG-06 to TRG-08 copy the registry's own behaviour: it accepts what it is given. The checks that a name is new, not reserved and not in use are the type definition store's (`AtlasTypeDefGraphStore`), ported in 1.4.

## Java origin

Apache Atlas `release-2.4.0`, `intg/src/main/java/org/apache/atlas/`:

- `type/AtlasTypeRegistry` (with `AtlasTransientTypeRegistry`, `TypeRegistryUpdateSynchronizer`, `TypeCache`, `TypeDefCache`), `AtlasType`, `AtlasBuiltInTypes`, `AtlasArrayType`, `AtlasMapType`, `AtlasEnumType`, `AtlasStructType` (with `AtlasAttribute`): the definition side only (DD-025)
- `AtlasErrorCode`, `exception/AtlasBaseException`
- tests: `intg/src/test/java/org/apache/atlas/type/TestAtlasTypeRegistry.java`, `TestAtlasStructType.java`, `TestAtlasArrayType.java`, `TestAtlasMapType.java`, `TestAtlasEnumType.java`

## Deviations

None. The update lock is held per server process; keeping several processes' registries in step is the store's (1.4).

## Acceptance

- `libs/python/aurelius-atlas-typesystem/tests/` — TRG-01 to TRG-16, run by `nx test aurelius-atlas-typesystem -c ci`.
- `libs/python/aurelius-atlas-model/tests/` — the error codes and messages (TRG-15).
- `apps/aurelius-atlas-server/tests/` — still green after the errors move (DD-023).
- `uv run aurelius-atlas-trace check`.

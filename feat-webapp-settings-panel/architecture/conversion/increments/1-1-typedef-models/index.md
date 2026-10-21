# 1.1 Typedef models

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-020, DD-021, DD-022; relies on DD-002, DD-013, ADR 046

## Scope

The data shapes of Atlas type definitions, in a new library without I/O, `libs/python/aurelius-atlas-model` (package `aurelius_atlas_model`, [DD-002](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)):

- the six type definitions: enum, struct, classification, entity, relationship and business metadata, with their parts (attribute, constraint, enum element, relationship end and relationship attribute definitions);
- the type definition header and `AtlasTypesDef`, the body of `/v2/types/typedefs`;
- reading them from and writing them to the JSON Atlas uses on its REST API, and the small helpers the Java classes offer (attribute and element lookup, super types, built-in type names).

No endpoint changes; the server does not use the library yet.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Resolving type names, supertypes and constraints; validation errors | 1.2 |
| Defaults the type registry fills in (relationship category, tags, …) | 1.3 |
| Storing type definitions; the built-in models at start-up | 1.4, 1.5 |
| `/v2/types/...`; malformed bodies answered with Atlas's error and 400 | 1.6 |
| Order-insensitive comparison of set-valued arrays in parity scenarios | 1.6 (DD-013) |
| The paged lists (`AtlasStructDefs`, … built on `PList`) | 1.6 |

## Semantics

"Reading" is what Atlas's Jackson mapper does with a REST request body; "writing" is what it puts in a response. Atlas serialises the models with Jackson 2.12 (`AtlasJsonProvider`, no date or naming customisation) and the annotations on each class ([DD-020](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/design-log/#dd-020-typedef-models-are-pydantic-models-that-read-and-write-atlass-json>)).

| Id | Rule |
| --- | --- |
| TDM-01 | Every field is read and written under the name of its Java getter: `isOptional`, `valuesMinCount`, `includeInNotification`, `endDef1`, `relationshipAttributeDefs`, `businessAttributeDefs`, … |
| TDM-02 | Writing leaves out a field whose value is null; an empty list, set or map is written |
| TDM-03 | Reading ignores fields the model does not have |
| TDM-04 | Each type definition writes its `category` (`ENUM`, `STRUCT`, `CLASSIFICATION`, `ENTITY`, `RELATIONSHIP`, `BUSINESS_METADATA`), fixed by its kind; a `category` in the input is ignored. The header reads and writes `category` like any field |
| TDM-05 | `createTime` and `updateTime` are written as milliseconds since the epoch, and read from such a number or from an ISO-8601 date-time string ([DD-022](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/design-log/#dd-022-typedef-timestamps-are-aware-datetimes-written-as-epoch-milliseconds>)) |
| TDM-06 | `attributeDefs` (struct and its kinds), `elementDefs` (enum), `superTypes` (classification, entity) and `entityTypes` (classification) are never null: missing, null or empty reads as empty |
| TDM-07 | Of attribute definitions with the same name, compared without case, only the last is kept, at its own position; an attribute definition without a name is dropped |
| TDM-08 | Of enum elements with the same value, compared without case, only the last is kept, at its own position; an element without a value is dropped |
| TDM-09 | `superTypes`, `subTypes` and `entityTypes` hold each name once ([DD-021](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/design-log/#dd-021-set-valued-fields-keep-each-name-once-in-first-seen-order>)) |
| TDM-10 | An attribute definition without them reads as `isOptional` false, `cardinality` `SINGLE`, `valuesMinCount` and `valuesMaxCount` -1, `isUnique`, `isIndexable` and `includeInNotification` false, `searchWeight` -1; an explicit null reads as false or 0, as in Java |
| TDM-11 | An empty `constraints` list reads as null and is not written; `options` maps are copied |
| TDM-12 | A relationship end without them reads as `cardinality` `SINGLE`, `isContainer` and `isLegacyAttribute` false; a relationship definition keeps `relationshipCategory`, `propagateTags` and its ends null when they are not given |
| TDM-13 | `AtlasTypesDef` reads each of its six lists as empty when missing and keeps an explicit null, which it does not write |
| TDM-14 | Type categories, cardinalities, index types, relationship categories and tag propagations are read and written by their Java names, with case; any other value is rejected |
| TDM-15 | Scalars are coerced as Jackson 2.12 coerces them by default: a number into a string field, a numeric or boolean string into a number or boolean field. A value that cannot be coerced, such as an object where a string is expected, is rejected with an error that names the field |
| TDM-16 | Attribute definitions and enum elements are found, replaced and removed by name or value without case; super types and entity types by exact name. Options and constraint parameters are read and set by exact key, a constraint's type is compared without case, and the `isSoftReference` and `isAppendOnPartialUpdate` options are true only for the value `true`, without case |
| TDM-17 | `AtlasTypesDef` is empty when all six lists are empty or null, and tells whether it holds a type definition of a kind by exact name |
| TDM-18 | A header made from a type definition carries its `guid`, `name`, `category` and `serviceType` |
| TDM-19 | `array<T>` and `map<K,V>` type names are built as Atlas builds them, and the primitive, built-in and relationship attribute type names are Atlas's |
| TDM-20 | Writing a model and reading the result gives an equal model; the type definitions of Atlas's `0010-base_model.json` and `0011-glossary_model.json` read without error |

TDM-06 to TDM-13 are the Java setters' and constructors' normalisations, which run when Jackson reads a body: a client that sends a duplicate attribute or no `cardinality` sees the normalised definition in the response.

## Java origin

Apache Atlas `release-2.4.0`, `intg/src/main/java/org/apache/atlas/model/`:

- `typedef/AtlasBaseTypeDef`, `AtlasStructDef` (with `AtlasAttributeDef`, `AtlasConstraintDef`), `AtlasEnumDef` (with `AtlasEnumElementDef`), `AtlasClassificationDef`, `AtlasEntityDef` (with `AtlasRelationshipAttributeDef`), `AtlasRelationshipDef`, `AtlasRelationshipEndDef`, `AtlasBusinessMetadataDef`, `AtlasTypeDefHeader`, `AtlasTypesDef`
- `TypeCategory`
- `webapp/.../web/util/AtlasJsonProvider`: the REST mapper (Jackson defaults, big decimals for floats)
- tests: `intg/src/test/java/org/apache/atlas/model/typedef/TestAtlas*Def.java`

## Deviations

None. Java writes sets in `HashSet` order, which Atlas does not define; parity scenarios will compare those arrays without order (DD-013, from 1.6).

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — TDM-01 to TDM-20, with JSON bodies taken from Atlas's model tests and `addons/models`, run by `nx test aurelius-atlas-model -c ci`.
- `uv run aurelius-atlas-trace check` — every public function and rule is named by a test.

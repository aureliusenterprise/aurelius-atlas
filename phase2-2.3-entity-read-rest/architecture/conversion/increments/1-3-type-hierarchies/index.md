# 1.3 Type hierarchies

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-026, DD-027; relies on DD-021, DD-024, DD-025

## Scope

The parts of the type system that link types to each other, in `aurelius-atlas-typesystem`:

- entity and classification hierarchies: super types, all super and sub types, inherited attributes, the root types with the system attributes, and the sub types written back to the definitions;
- the entity type's derived attributes: header and minimal-info attributes, the display-text attribute, owned references and whether the type is internal;
- the entity types a classification may be applied to;
- relationship types: their ends, label and the relationship attributes they add to entity types, which are inherited and written back to the entity definitions with the tag-propagation edges;
- business metadata types: their attributes, the entity types they apply to, and the business attributes written back to the entity definitions;
- Atlas error messages formatted as Java's `MessageFormat` formats them.

No endpoint changes.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Dynamic attributes (`dynAttribute:` templates) and their evaluation order | 2.4 (DD-026) |
| The root entity type's lookup of business attributes for search | 4.1 (DD-026) |
| Logging relationship definitions an entity attribute lacks (`reportMissingRelationshipDef`) | not ported |
| Index-query strings of type names (`getTypeAndAllSubTypesQryStr`) | dropped (DD-025) |

## Semantics

| Id | Rule |
| --- | --- |
| THY-01 | An entity type's super types must be entity types and a classification's must be classifications, else `INCOMPATIBLE_SUPERTYPE` (400) with the super type's name first and the type's second, as Java passes them |
| THY-02 | A type that reaches itself through its super types fails with `CIRCULAR_REFERENCE` (400), naming the type and the types visited on the way, as `[A, B]` |
| THY-03 | A type's attributes are those of all its super types, depth first in the order the super types are given, then its own. A name defined by two different types of the hierarchy fails with `ATTRIBUTE_NAME_ALREADY_EXISTS_IN_ANOTHER_PARENT_TYPE` (400); a super type reached twice is not a conflict |
| THY-04 | Each type knows its super types, all super types and the sub types and all sub types that every other type's super types give it, each also with the type itself. Sub types are written to the definition's `subTypes` |
| THY-05 | `__ENTITY_ROOT` and `__CLASSIFICATION_ROOT` hold Atlas's system attributes (`__guid`, `__typeName`, `__timestamp`, …); every entity and classification type finds them by name after its own and inherited attributes. Root types are not registered, and their attribute names are not qualified |
| THY-06 | An entity type's header attributes are its unique attributes and `name`, `description`, `owner` and `createTime`; its minimal-info attributes add those its `schemaAttributes` option lists. Its display-text attribute is its `displayTextAttribute` option, else a direct super type's option, else any super type's, when that names an attribute. It is internal when `__internal` is among its super types. Its owned references are the attributes and relationship attributes with `ownedRef` |
| THY-07 | A classification applies to its `entityTypes` and all their sub types (an unknown name fails with `TYPE_NAME_NOT_FOUND`), narrowed by what its super types allow. Super types whose allowed types do not overlap fail with `CLASSIFICATIONDEF_PARENTS_ENTITYTYPES_DISJOINT`, and own types outside them with `CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET` (400); with no own types it applies where its super types allow; with no restriction anywhere, to every entity type |
| THY-08 | A relationship's two ends need a type (`MISSING_MANDATORY_ATTRIBUTE`, `endDef1.type`) that is an entity type (`RELATIONSHIPDEF_INVALID_END_TYPE`) and a name. No end may be `LIST`; not both ends may be containers; a container needs `AGGREGATION` or `COMPOSITION`, which in turn need a container; a `COMPOSITION` end with `SET` must be the container. Each breach has its Atlas code (400) |
| THY-09 | A relationship's label is its `relationshipLabel`, else `r:` and its name when neither end is a legacy attribute, else `__` and the qualified name of the legacy end's attribute |
| THY-10 | Each end adds a relationship attribute named after the end to its entity type. When the type has no attribute of that name, the attribute is new: it holds the other end's type (`array<…>` for `SET`), with the end's cardinality, optional except on a composition's child end, and `ownedRef` on a composition's container end. Otherwise the existing attribute is used and marked legacy. Each has the relationship's name, edge label and an edge direction (`OUT`, `IN` or `BOTH`) |
| THY-11 | Sub types inherit relationship attributes; the first a type gets per attribute and relationship stays. They are written to the entity definition's `relationshipAttributeDefs` with their relationship's name and legacy flag, and with `isAppendOnPartialUpdate` when the type's `appendRelationshipsOnPartialUpdate` option lists them. A relationship's label is the type's tag-propagation edge when its `propagateTags` sends classifications from that type |
| THY-12 | A business metadata attribute may not hold a struct, classification or business metadata type, nor an array or map of one (`BUSINESS_METADATA_DEF_ATTRIBUTE_TYPE_INVALID`); its `applicableEntityTypes` option must name entity types; a string attribute needs a `maxStrLength` option (`MISSING_MANDATORY_ATTRIBUTE`). Business attributes are added to the entity types they apply to and their sub types, found as `bm.attribute`, and written to the entity definition's `businessAttributeDefs` |
| THY-13 | Error messages follow `MessageFormat`: an apostrophe starts or ends quoted text, which is copied as is and loses the apostrophe, and two apostrophes are one; collection parameters are written as `[a, b]` |

THY-04, THY-11 and THY-12 change the definitions the registry holds, as Java does. The definitions Types REST returns (1.6) therefore carry `subTypes`, `relationshipAttributeDefs` and `businessAttributeDefs`.

## Java origin

Apache Atlas `release-2.4.0`, `intg/src/main/java/org/apache/atlas/type/`:

- `AtlasEntityType` (with `AtlasRootEntityType`), `AtlasClassificationType`, `AtlasRelationshipType`, `AtlasBusinessMetadataType` (with `AtlasBusinessAttribute`), `AtlasStructType.AtlasAttribute` (edge labels and directions), `Constants`: the definition side (DD-025)
- `java.text.MessageFormat`, as `AtlasErrorCode.getFormattedErrorMessage` uses it
- tests: `intg/src/test/java/org/apache/atlas/type/TestAtlasTypeRegistry.java` (hierarchies), `TestAtlasEntityType.java`, `TestAtlasClassificationType.java`, `TestAtlasRelationshipType.java`, `TestAtlasBusinessMetadataType.java`

## Deviations

None. Where Java iterates a `HashSet` or `HashMap` (all super types, relationship attributes), the first-seen order is used ([DD-021](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/conversion/design-log/#dd-021-set-valued-fields-keep-each-name-once-in-first-seen-order>), [DD-027](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/conversion/design-log/#dd-027-derived-type-sets-keep-first-seen-order>)).

## Acceptance

- `libs/python/aurelius-atlas-typesystem/tests/` — THY-01 to THY-12, run by `nx test aurelius-atlas-typesystem -c ci`, with Atlas's `0010-base_model.json` and `0011-glossary_model.json` resolved in full.
- `libs/python/aurelius-atlas-model/tests/` — THY-13.
- `uv run aurelius-atlas-trace check`.

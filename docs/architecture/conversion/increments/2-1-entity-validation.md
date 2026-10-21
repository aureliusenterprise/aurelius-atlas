# 2.1c Entity validation

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-042, DV-13; relies on DD-025, DD-037, DD-039, DD-040, DD-041

The last part of increment 2.1 (2.1a ported the entity models, 2.1b the value types): the value side of the
struct, classification, entity and business metadata types, which check, normalise and default an instance
attribute by attribute (DD-025).

## Scope

In `aurelius-atlas-typesystem`, finishing DD-041: the struct, classification, entity, relationship and business
metadata types move out of `types.py` into one module each (`struct_type`, `classification_type`,
`entity_type`, `relationship_type`, `business_metadata_type`, with `attribute`, `edge_direction`,
`hierarchy_type` and `type_names`); `types.py` re-exports them. Then, for each type, `createDefaultValue`,
`isValidValue`, `getNormalizedValue`, `validateValue`, their `ForUpdate` variants, `areEqualValues`,
`normalizeAttributeValues` (and `ForUpdate`) and `populateDefaultValues`; the classification type's validity
periods and the entity type's relationship attributes.

Not in scope:

| Not delivered here                                                                                                  | Delivered by |
| ------------------------------------------------------------------------------------------------------------------- | ------------ |
| The relationship type's own value checks: they take an `AtlasRelationship`                                          | 3.1          |
| Business metadata attribute options on values (`maxStrLength`, `validPattern`): checked by the store, not the types | 5.3          |
| Using the types to validate entity writes (`EntityGraphDiscovery`, `AtlasEntityStoreV2`)                            | 2.2, 2.4     |
| Dynamic attributes (DD-026)                                                                                         | 2.4          |

## Semantics

A value is a Java value as DD-040 holds it; a struct value is an `AtlasStruct` (or a subclass) or a map. "The
attributes of a map" are its `attributes` map when it has a `typeName` key and an `attributes` map, else the map
itself (`AtlasTypeUtil.toStructAttributes`); "its relationship attributes" likewise
(`toRelationshipAttributes`), or none.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EVL-01 | A struct type takes a struct or a map. It is valid when each attribute the type itself defines has a valid value for its type, or no (null) value and is optional; super types check theirs. Any other value is invalid                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| EVL-02 | `validateValue` validates each such attribute's value as `<name>.<attribute>`; a mandatory attribute without a value adds `<name>.<attribute>: mandatory attribute value missing in type <type>`, unless the value is an entity with a relationship attribute of that name, or an incomplete entity, or a map whose relationship attributes have that name. A value that is no struct or map adds `<name>=<value>: invalid value for type <type>`                                                                                                                                                                                                                |
| EVL-03 | The `ForUpdate` variants check, validate and normalise only the attributes that have a value and a definition in the type; a missing mandatory attribute is no error                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| EVL-04 | Normalising sets each attribute the type defines that is present to its normalised value (an invalid one becomes null; a null mandatory one the type's default), and adds each missing mandatory attribute with its default; the struct or map itself is the normalised value, or null when it is invalid                                                                                                                                                                                                                                                                                                                                                        |
| EVL-05 | The default of an attribute is its type's `createDefaultValue` of the attribute's `defaultValue`. `populateDefaultValues` sets every mandatory attribute to its default, replacing a value it has; `createDefaultValue` is a new struct, classification or entity of the type with its mandatory defaults, whatever value it is given                                                                                                                                                                                                                                                                                                                            |
| EVL-06 | Two struct values are equal when both are null, or both are structs or maps (read by Java's map constructor) of type names equal ignoring case whose every attribute is equal by its type. A string fails, as Java's `ClassCastException`                                                                                                                                                                                                                                                                                                                                                                                                                        |
| EVL-07 | A classification type checks its super types first, then its validity periods, then its own attributes. Each validity period of a classification (not of a map) has a known time zone (`INVALID_TIMEBOUNDRY_TIMEZONE`), a `startTime` and `endTime` that parse strictly as `yyyy/MM/dd HH:mm:ss` in that zone (`INVALID_TIMEBOUNDRY_START_TIME`, `…END_TIME`), and an end not before its start (`INVALID_TIMEBOUNDRY_DATERANGE`); `validateValue` adds each such message once. A known zone is a tz database id, one of Java's legacy three-letter ids, a custom `GMT±h[h][[:]mm]` offset or `GMT`; a period without a zone is in the server's zone (DD-042)     |
| EVL-08 | An entity type checks its super types first, then its own attributes, then its relationship attributes. A relationship attribute is the type's attribute of that name for the value's relationship type (that of a related object id, a map's `relationshipType`, or the first element or map value that has one), else the first; a value of a relationship attribute whose type holds object ids or entities is checked by the object id type, any other by its type. `validateValue` adds a missing mandatory relationship attribute (not for an incomplete entity), and for a value that is no entity or map adds `<name>: invalid value type '<Java class>` |
| EVL-09 | Normalising an entity also normalises the value of each relationship attribute that holds object ids or entities                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| EVL-10 | A business metadata type takes every value; its default and every normalised value are null                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| EVL-11 | Atlas's type tests hold: `testStructType…`, `testEntityType…` and `testClassificationType…` (`DefaultValue`, `IsValidValue`, `GetNormalizedValue`, `ValidateValue`, `TimebounderTimeZone`) on `ModelTestUtil`'s definitions, their random attribute types fixed; and `TestAtlasEntity` and `TestAtlasClassification`: a default value written to JSON, read back and normalised equals the original                                                                                                                                                                                                                                                              |

## Java origin

Apache Atlas `release-2.4.0`, `intg/src/main/java/org/apache/atlas/`:

- `type/AtlasStructType` (value side, `AtlasAttribute`), `AtlasClassificationType` (value side,
  `validateTimeBoundaries`, `isValidTimeZone`), `AtlasEntityType` (value side, relationship attributes),
  `AtlasRelationshipType` (struct side only), `AtlasBusinessMetadataType`
- `type/AtlasTypeUtil`: `toStructAttributes`, `toRelationshipAttributes`; `utils/AtlasEntityUtil.getRelationshipType`
- `model/TimeBoundary`, commons-validator `DateValidator` (strict, whole value), `java.util.TimeZone`
- tests: `intg/src/test/java/org/apache/atlas/type/TestAtlas{Struct,Entity,Classification}Type`,
  `model/instance/TestAtlas{Entity,Classification}`, `model/ModelTestUtil`

## Deviations

DV-13: an entity type given a map without relationship attributes fails in Atlas with a `NullPointerException`
(`toRelationshipAttributes` answers null), an internal error, when the type has relationship attributes; Aurelius
Atlas checks the map as one without relationship attribute values.

## Acceptance

- `libs/python/aurelius-atlas-typesystem/tests/values/` — EVL-01 to EVL-11, one test file per type module; a
  port of `ModelTestUtil` with its random attribute types fixed.
- `uv run aurelius-atlas-trace check`.

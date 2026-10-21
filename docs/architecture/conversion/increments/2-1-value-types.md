# 2.1b Value types

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-039, DD-040, DD-041, DV-11; relies on DD-024, DD-025, DD-037, DD-038

Increment 2.1 is split in three, each within the size limit of ADR 051: 2.1a ported the entity models,
2.1b, this specification, ports the value side of the built-in, enum, array and map types, and 2.1c
(`2-1-entity-validation.md`) the value side of the struct, classification, entity, relationship and business
metadata types, which validates and normalises entities attribute by attribute (DD-025).

## Scope

In `aurelius-atlas-typesystem`, one module per Java type class (DD-041):

| Module                                 | Java class (`org.apache.atlas.type`)                                                                      |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `atlas_type`                           | `AtlasType`: the value contract every type has                                                            |
| `builtin/boolean_type` … `string_type` | `AtlasBuiltInTypes.Atlas{Boolean,Byte,Short,Int,Long,Float,Double,BigInteger,BigDecimal,Date,String}Type` |
| `builtin/object_id_type`               | `AtlasBuiltInTypes.AtlasObjectIdType`                                                                     |
| `enum_type`, `array_type`, `map_type`  | `AtlasEnumType`, `AtlasArrayType`, `AtlasMapType`                                                         |
| `java`                                 | the Java number and text conversions the types rely on                                                    |

`AtlasType`, `ObjectIdType`, `EnumType`, `ArrayType` and `MapType` move out of `types.py`, which re-exports
them. In `aurelius-atlas-model`: the Atlas JSON codec (`codec`, DD-039), Java's map constructors of
`AtlasStruct`, `AtlasObjectId` and `AtlasRelatedObjectId`, and `to_json` writing values as the codec needs
them.

For each type: `createDefaultValue`, `createOptionalDefaultValue`, `createDefaultValue(value)`,
`isValidValue`, `getNormalizedValue`, `validateValue`, their `ForUpdate` variants and `areEqualValues`.

No endpoint changes; nothing validates entities yet.

Not in scope:

| Not delivered here                                                                         | Delivered by |
| ------------------------------------------------------------------------------------------ | ------------ |
| The value side of struct, classification, entity, relationship and business metadata types | 2.1c         |
| Attribute options checked on values (`maxStrLength`, `validPattern`), time boundaries      | 2.1c         |
| Reading request bodies with the codec in the REST layer                                    | 2.3, 2.4     |

## Semantics

"Java value" below means what Atlas's Jackson mapper reads from a REST body, and the values Atlas's code
builds; DD-040 says how each is held in Python. A JSON integer is a Java `Integer`, `Long` or `BigInteger`
by its size; a JSON number with a fraction or exponent is a `BigDecimal` (`USE_BIG_DECIMAL_FOR_FLOATS`).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VAL-01 | The Atlas JSON codec reads a body as Jackson does: objects in order, arrays, strings, integers exactly, every number with a fraction or exponent as a decimal with its digits, booleans and null. It writes a decimal with its digits (`BigDecimal.toString`: `1.10`, `1E+3`), a date as epoch milliseconds, a float as its shortest decimal, NaN as the string `"NaN"`, and map keys as Java's text of the key; `to_json` leaves these values to it                                                                                                                                                                                                                                                |
| VAL-02 | Every type: null is valid and normalises to null. `validateValue` of an invalid value adds `<name>=<value>: invalid value for type <type>`, the value in Java's text (`String.valueOf`). The `ForUpdate` variants are the plain ones except for arrays and maps (VAL-12, VAL-13). `createDefaultValue(value)` is the default for null, else the normalised value; the optional default is the default, except for `string` (VAL-09). Two values are equal when both are null, or both normalise and their normalised values are equal; a value that does not normalise equals nothing                                                                                                               |
| VAL-03 | `boolean`: a boolean, or the string `true` or `false` in any case; default false                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| VAL-04 | `byte`, `short`, `int` and `long`: a number whose integer part, truncated toward zero, is in the type's range (a Java `float` or `double` converted as Java converts it, NaN as 0), normalised to that integer; or a string Java's `valueOf` parses: an optional sign and ASCII digits. Anything else, a boolean included, is invalid. Default 0                                                                                                                                                                                                                                                                                                                                                    |
| VAL-05 | `float` and `double`: a number within ±`Float.MAX_VALUE` or ±`Double.MAX_VALUE`, normalised to a 32-bit or 64-bit float (a `float` written as the shortest decimal of its 32-bit value); or a string Java's `valueOf` parses (trimmed; sign; decimal or hexadecimal digits; exponent; `NaN`; `Infinity`; an `f`, `F`, `d` or `D` suffix) to a finite value. Two values are equal when their normalised values differ by less than 1e-8. Default 0                                                                                                                                                                                                                                                   |
| VAL-06 | `biginteger`: a decimal or a string Java's `BigDecimal` parses, truncated toward zero; an integer as it is; a Java `float` or `double` converted to `long` as Java does. Default 0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| VAL-07 | `bigdecimal`: every number is valid. A decimal stays as it is and an integer beyond the `long` range becomes an exact decimal; 0 becomes `0`, and any other number becomes `BigDecimal.valueOf` of its Java `double` (`5` becomes `5.0`). A string is valid when Java's `BigDecimal` parses it. Default 0                                                                                                                                                                                                                                                                                                                                                                                           |
| VAL-08 | `date`: a number is the date that many milliseconds after the epoch (Java's `long` conversion). A string is parsed leniently as `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` in UTC (fields roll over, text after the pattern is ignored), else as a `long`. An empty string is valid but normalises to null. Default the epoch                                                                                                                                                                                                                                                                                                                                                                                   |
| VAL-09 | `string`: every value is valid and normalises to Java's text of it: numbers as Java writes them, `true`, maps as `{k=v, …}`, lists as `[a, b]`. Default `""`, optional default null                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| VAL-10 | `objectid`: an object id, or a map with a non-empty `guid`, or with a non-empty `typeName` and a non-empty `uniqueAttributes` map. A map normalises to a related object id when it has a `relationshipType` key, else to an object id, as Java's map constructors read it. Default `{"guid": "-1", "typeName": <object type>}`. Two object ids are equal after mapping their GUIDs through the GUID assignments: by GUID when both or neither GUID is assigned (non-empty, not starting with `-`), else by type name and unique attributes                                                                                                                                                          |
| VAL-11 | An enum type: a value whose Java text equals an element's value, ignoring case, normalised to that element's value; default the enum's default value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| VAL-12 | `array<T>`: a list whose size is within the minimum and maximum count, when set, and whose elements are valid. Normalising first parses a string as JSON (a string that is not a JSON array normalises to null), then normalises each element, keeping nulls; a wrong count or element normalises the whole array to null. `validateValue` adds `<name>: incorrect number of values. found=<n>; expected: minCount=<min>, maxCount=<max>` and validates each element as `<name>[<i>]`. The default holds the element's default once, or `minCount` times. A `LIST` equals element by element; a `SET` (each value once, Java equality) has the same size and each element equals one of the other's |
| VAL-13 | `map<K,V>`: a map whose keys and values are valid. Normalising first parses a string as JSON, then normalises keys and values, keeping null values; an invalid key or value normalises the whole map to null. `validateValue` adds `<name>.<key>: invalid key for type <type>` and validates each value as `<name>.<key>`. The default maps the key's default to the value's, or is empty when the key has none. Null equals an empty map; otherwise equal maps have the same size and equal values by key                                                                                                                                                                                          |
| VAL-14 | `AtlasStruct`, `AtlasObjectId` and `AtlasRelatedObjectId` are made from a map as their Java map constructors do: a struct takes `typeName` and `attributes`, or the whole map when it has no `attributes` map; an object id takes `guid`, `typeName` and a `uniqueAttributes` map; a related object id adds `relationshipGuid`, `relationshipType`, `relationshipStatus` and `relationshipAttributes` as a struct                                                                                                                                                                                                                                                                                   |
| VAL-15 | Atlas's type tests hold: the valid, limit, negative and invalid values of `TestAtlas{Boolean,Byte,Short,Int,Long,Float,Double,BigInteger,BigDecimal,Date,String,ObjectId}Type`, `TestAtlasArrayType` and `TestAtlasMapType`, each Java value held as DD-040 says                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## Java origin

Apache Atlas `release-2.4.0`:

- `intg/src/main/java/org/apache/atlas/type/`: `AtlasType`, `AtlasBuiltInTypes` (all nested types and
  `toBigInteger`), `AtlasEnumType`, `AtlasArrayType`, `AtlasMapType`, `AtlasTypeUtil.isAssignedGuid`
- `intg/.../model/instance/`: the map constructors of `AtlasStruct`, `AtlasObjectId`, `AtlasRelatedObjectId`
- `intg/.../model/typedef/AtlasBaseTypeDef`: `SERIALIZED_DATE_FORMAT_STR` and the UTC date formatter
- `intg/.../utils/AtlasJson`: `fromJson`, the mapper arrays and maps parse strings with
- `webapp/.../web/util/AtlasJsonProvider`: `USE_BIG_DECIMAL_FOR_FLOATS`
- tests: `intg/src/test/java/org/apache/atlas/type/TestAtlas*Type.java` (VAL-15)

## Deviations

DV-11: a `float` attribute given a decimal or integer beyond the `double` range makes Atlas fail with
`NumberFormatException` (`new BigDecimal(Infinity)` in `AtlasFloatType.isValidRange`), an internal error;
Aurelius Atlas treats the value as invalid.

## Acceptance

- `libs/python/aurelius-atlas-typesystem/tests/values/` — VAL-02 to VAL-13 and VAL-15, one test file per
  module, Atlas's value lists translated by DD-040.
- `libs/python/aurelius-atlas-model/tests/` — VAL-01 and VAL-14.
- `uv run aurelius-atlas-trace check`.

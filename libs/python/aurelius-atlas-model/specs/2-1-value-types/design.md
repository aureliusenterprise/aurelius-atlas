# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-039. One Atlas JSON codec reads floats as decimals and writes them with their digits

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** `aurelius_atlas_model.codec` holds Atlas's JSON reading and writing. `loads` reads every number
with a fraction or exponent as a `Decimal`, as Jackson's `USE_BIG_DECIMAL_FOR_FLOATS` does. `dumps` writes a
`Decimal` with its digits, a `datetime` as epoch milliseconds, NaN as the string `"NaN"`, and map keys as
Java's text of the key. `AtlasModel.to_json` dumps in Pydantic's Python mode, so attribute values keep these
types for the codec; typed timestamps are written as epoch milliseconds in both modes. The server's
`AtlasJSONResponse` writes its content with `dumps`. This settles DD-038.

**Reason.** A `bigdecimal` attribute keeps the digits it was given (`1.10`), and normalised dates are Java
`Date` values that Jackson writes as numbers, even inside untyped attribute maps. Python's `json` turns a
`Decimal` into a float, and Pydantic's JSON mode turns it, and a `datetime`, into a string.

**Alternatives.** A custom Pydantic serializer per field: values inside `dict[str, Any]` have no field of
their own. Converting decimals to floats: loses digits a client sent.

**Consequences.** A double is written with Python's shortest form (`10000000.0`), where Jackson writes
`Double.toString` (`1.0E7`): the same number in another notation, equal for every JSON reader and for the
parity comparison. Request bodies with entity values are read with `loads` from 2.3 on.

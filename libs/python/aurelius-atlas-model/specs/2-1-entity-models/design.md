# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-037. Instance models are one module per Java class

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-20

**Decision.** The entity models live in the package `aurelius_atlas_model.instance`, one module per Java
class, nested classes and enums included (`entity`, `entity_status`, `entity_with_ext_info`, …). The package
re-exports every model. The JSON conventions all models share (`AtlasModel`, the timestamp, Java boolean, int
and set types) move from `typedef` to `aurelius_atlas_model.base`; `typedef` imports them from there.

**Reason.** Atlas organises its models as one class per file; a reader who knows a Java class finds its port
by name, and each module stays small enough to read whole. The typedef models were ported into one module
(1.1); the instance models are more numerous and depend on each other in one direction only (struct, then
entity, header, ext info), which modules make visible.

**Alternatives.** One `instance.py`, as `typedef.py`: about as long as all of `typedef.py` again, mixing
seventeen classes. Importing the shared conventions from `typedef`: makes the instance models depend on the
typedef module for reasons unrelated to type definitions.

**Consequences.** Tests follow the layout, one file per module under `tests/instance/`; the four enums,
which have no behaviour of their own, share one. Splitting
`typedef.py` the same way is possible later without changing its imports, through its re-exports.

### DD-038. Attribute values stay plain JSON values until their types read them

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-20

**Decision.** The models of 2.1a keep attribute values (`attributes`, `relationshipAttributes`,
`uniqueAttributes`, business attributes) as the JSON values Python reads: objects, arrays, strings, integers,
floats, booleans and null. Atlas's REST mapper reads floats as `BigDecimal` (`USE_BIG_DECIMAL_FOR_FLOATS`)
and writes them back with their digits (`1.10`, `1E+3`); that is designed with the `bigdecimal`, `float` and
`double` types in 2.1b.

**Reason.** An untyped value reaches a response only after its attribute's type normalised it (2.1b, then
the stores), so the digits of a float matter only where a type keeps them. Keeping them in 2.1a would need
a JSON reader and writer of its own for every model before any type needs it.

**Alternatives.** Read every float as `Decimal` now: Pydantic writes a `Decimal` as a JSON string, so every
writer would need a custom encoder, designed without the type that motivates it.

**Consequences.** 2.1b decides how a `bigdecimal` value is read from a body and written back exactly, and
applies it to these models.

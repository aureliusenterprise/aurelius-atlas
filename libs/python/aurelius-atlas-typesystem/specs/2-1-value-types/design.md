# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-040. Java values are held as the Python values closest to them

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** A Java `Integer`, `Long`, `BigInteger`, `Byte` or `Short` is a Python `int`; which of them it
was follows from its size, as Jackson chooses by size (`Integer` within 32 bits, `Long` within 64,
`BigInteger` beyond). A `BigDecimal` is a `Decimal`, a `Double` a `float`, and a `Float` a `float` holding the
shortest decimal of the 32-bit value. A `Boolean` is a `bool`, never a number. A `Date` is an aware UTC
`datetime` with millisecond precision. The conversions Java applies between them (`longValue`, `intValue`,
`floatValue`, `toBigInteger`, `BigDecimal.valueOf(double)`, `valueOf(String)`, `String.valueOf`) are
functions of `aurelius_atlas_typesystem.java`, each named after its Java original.

**Reason.** The types branch on the Java class of a value (`instanceof Long`, `instanceof BigDecimal`), and
their results depend on Java's arithmetic: truncation, saturation, 32-bit rounding. Values from a JSON body
can only be integers, decimals, strings, booleans, lists and maps, so the Python types need only tell those
apart; Java `Float` and `Double` arise from Atlas's own code and from Atlas's tests.

**Alternatives.** Wrapper classes for every Java number type: every value would need wrapping on reading
and unwrapping on writing, for distinctions JSON cannot express.

**Consequences.** A `float` value written and read back is the same 32-bit value. An `Integer` and a `Long`
of equal value cannot be told apart, and give the same result in every type. A `BigInteger` within 64 bits
cannot be told apart from a `Long` either; `bigdecimal` treats them differently (`1` against `1.0`), but JSON
never yields one, because Jackson reads such integers as `Integer` or `Long`.

### DD-041. The type system is one module per Java type class too

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** As DD-037 for the models: the types the value side adds or changes get one module each,
`atlas_type`, `enum_type`, `array_type`, `map_type`, and `builtin/<name>_type` for each nested class of
`AtlasBuiltInTypes`. `types.py` keeps the struct, classification, entity, relationship and business
metadata types, which 2.1c moves the same way, and re-exports the moved classes.

**Reason.** The value side roughly doubles the type classes; one file of all of them would pass two
thousand lines. A reader who knows Atlas's `AtlasArrayType` finds `array_type`.

**Alternatives.** Adding the value side to `types.py`: one module far beyond what anyone reads whole.

**Consequences.** `from aurelius_atlas_typesystem.types import ArrayType` keeps working; new code imports
from the class's own module.

### DD-042. A validity period without a time zone is in UTC

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-22

**Decision.** A classification's validity period without a `timeZone` is read in UTC, where Atlas reads it in
its JVM's default time zone (`TimeZone.getDefault()`). Java's time zone ids are matched with Python's tz
database (`zoneinfo`), Java's legacy three-letter ids (`ZoneId.SHORT_IDS`, such as `PST` and `IST`) and its
custom `GMT±h[h][[:]mm]` offsets.

**Reason.** Atlas's default zone is whatever its host is set to; the server image runs in UTC, so UTC is the
same answer for a container deployment, and it does not change with where the code happens to run. The tz
database holds every zone Java's `TimeZone` resolves except the legacy short ids, which Java maps to tz ids.

**Alternatives.** The local zone of the Python process: makes validation depend on the developer's machine.
A setting for the default zone: nothing asks for one yet.

**Consequences.** A validity period of `2026/01/01 00:00:00` without a zone means midnight UTC. The time zone
list must stay in step with Java's; the tz database of the image (the `tzdata` package) supplies it.

# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-020. Typedef models are Pydantic models that read and write Atlas's JSON

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** Each Atlas typedef class is a Pydantic model in `aurelius_atlas_model.typedef` with
snake_case attributes and the Java getter names as aliases. `model_validate` reads a request body and
`to_json` writes a response body: aliases, null fields left out, empty collections kept. Unknown fields
are ignored. The Java setters' normalisations run as `_`-prefixed validators, so they apply when a body
is read and when a model is built in code, as the Java constructors and setters do.

**Reason.** Pydantic is already the workspace's modelling library (settings, store) and FastAPI reads and
writes it natively, so 1.6 needs no mapping layer. Atlas writes with Jackson `NON_NULL`, which is
Pydantic's `exclude_none`; empty collections stay because Jackson keeps them (DD-013 compares exactly).

**Alternatives.** Dataclasses with a hand-written JSON codec: no dependency, but every rule of TDM-01 to
TDM-15 would be custom code. Generating models from Atlas's JSON schema: Atlas publishes none, and the
normalisations live in Java setters a schema cannot express.

**Consequences.** Response bodies must be written with `to_json` (or its `exclude_none`, `by_alias`
dump), never with FastAPI's default response model serialisation. Later model packages (entities in 2.1)
follow the same pattern.

### DD-021. Set-valued fields keep each name once, in first-seen order

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `superTypes`, `subTypes` and `entityTypes` are lists without duplicates, kept in the order
the names were first given.

**Reason.** Java holds them in a `HashSet` and writes them in hash order, which Atlas does not define and
no client can rely on. A Python `set` would make our order vary from run to run; first-seen order is
stable and keeps what the client sent.

**Alternatives.** Reproduce Java's `HashSet` iteration order: possible from `String.hashCode` and the
table size, but it would copy an accident of the implementation. Sorted order: stable, but reorders
what clients send.

**Consequences.** The JSON order of these arrays can differ from Atlas's. Parity scenarios compare them
without order, through the option DD-013 foresees, which 1.6 adds with the first scenario that needs it.

### DD-022. Typedef timestamps are aware datetimes, written as epoch milliseconds

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `createTime` and `updateTime` are timezone-aware UTC `datetime`s. They are written as
integer milliseconds since the epoch and read from a number, a string of digits or an ISO-8601
date-time string.

**Reason.** Atlas's REST mapper has no date serialiser, so Jackson writes `java.util.Date` as epoch
milliseconds and its `StdDateFormat` reads numbers, digit strings and ISO-8601. Pydantic would read a
bare integer as seconds or milliseconds depending on its size, so the conversion is explicit.

**Alternatives.** Keep the raw integer: exact, but every caller would convert. Write ISO-8601 strings:
readable, but a visible difference from Atlas.

**Consequences.** Jackson's RFC 1123 form (`Tue, 17 Oct 2026 10:00:00 GMT`) is not read. No Atlas client
is known to send it; if one does, it becomes a deviation.

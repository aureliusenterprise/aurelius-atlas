# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-052. A request is mapped in memory and written once; a lost race runs it again

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** `EntityWriter` reads every stored entity a create or update request names, discovers and
resolves its references, and maps its entities to their new stored form in memory, together with the
entities EWR-12 touches. The response's headers are built from that form. The result is one
`EntityStore.write` (ENS-07), each changed entity conditional on the version it was read in (ENS-08). When
the write loses a race, the whole request is read, mapped and written again, once; a second loss, or a unique
value another entity holds, is answered with `INTERNAL_ERROR` naming the cause (DV-20).

**Reason.** Atlas maps a request onto vertices inside one graph transaction and commits at the end; mapping
onto documents in memory and writing them in one all-or-nothing write is the same shape on Elasticsearch
(DD-046). Running the request again on the newer state is what a client would do, as DD-029 does for types.

**Alternatives.** Writing each entity as it is mapped: a failure part-way would leave a half-written request
for recovery to undo, and headers would be read from the index. Answering a lost race with an error at once:
two clients updating different attributes of an entity would fail where Atlas, serialising them, succeeds.

**Consequences.** A request's memory grows with its entities, as Atlas's transaction does. A unique value
clash is no `400`: Atlas resolves an entity by its unique values before writing, so a clash needs an update
that moves a value onto another entity, or two new entities with the same value in one request.

### DD-053. Relationship attribute values are resolved, but stored only as legacy attributes until 3.1

- **Status:** Superseded by DD-064
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** Until 3.1 stores relationships, a relationship attribute's value in a write is discovered,
resolved, checked and normalised as Atlas does, so its errors are Atlas's. It is stored only when the entity's
type has an attribute of the same name (a legacy relationship end, such as `hive_table.db`), as that
attribute's value (DD-049); a relationship attribute without such an attribute is not stored (DV-22).

**Reason.** A legacy end is read from `attributes` (DD-050, DV-18); storing it there keeps what clients
write readable. Storing other relationship values needs relationship instances, their GUIDs and both ends,
which is 3.1's.

**Alternatives.** Rejecting relationship attributes until 3.1: requests Atlas accepts, such as the hook
models', would fail. Storing them as plain references on one end: 3.1 would have to migrate them.

**Consequences.** 3.1 replaces this: relationship values become relationships, and the legacy attributes'
values move to them.

### DD-054. Dynamic attributes are evaluated in first-seen dependency order

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** An entity type's dynamic attributes are ordered by a depth-first topological sort over their
templates, visiting them in the order their `dynAttribute:` options appear, so that an attribute another
template names is evaluated first.

**Reason.** Java sorts the same graph but starts from the keys of a `HashMap`; where the dependencies leave
the order open, first-seen order is stable, as DD-027 chooses for derived type sets.

**Alternatives.** Sorting by name: stable too, but unrelated to the definition.

**Consequences.** Independent dynamic attributes may be evaluated in another order than Atlas's; their values
do not depend on it.

### DD-055. Scenarios name what they create with a per-run value

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** The parity harness provides `{run}`, a value unique to each run of a scenario, in letters and
digits, before any stage has saved a value. Entity scenarios name their types and entities with it, and
leave them in the store until 2.5 lets them delete what they created (DD-035).

**Reason.** The dev store keeps its contents between runs. A scenario that creates an entity again on a
second run would find it, update it and get a different answer; a type in use cannot be deleted.

**Alternatives.** Deleting the entity index before scenarios: other tests and a developer's data share the
dev store. Waiting for 2.5: 2.4's writes would have no parity check (DD-051).

**Consequences.** Each run of the entity scenarios leaves a few types and entities in the dev store until
2.5; CI starts from an empty store.

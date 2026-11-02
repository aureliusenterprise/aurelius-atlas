# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-028. The type definitions are one Elasticsearch document

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** All stored type definitions are one document, `typedefs`, in the index
`aurelius-atlas-typedefs` (through an alias, so a reindex can swap it). The document holds the
definitions in their stored form (TDS-05, TDS-06), grouped by kind as in `AtlasTypesDef`. Every change
replaces the whole document, guarded by `if_seq_no` and `if_primary_term`.

**Reason.** Atlas changes several definitions in one graph transaction: `createTypesDef` stores all of
a request or none (TDS-10). Elasticsearch has no transaction across documents, but writes one document
atomically, so one document makes every typedef change atomic and its sequence number a single version
of all types (DD-029). The registry, not Elasticsearch, answers every query over types; the document is
read whole at start-up and on change. Atlas's built-in models with all patches are about 1 MB of JSON,
well inside Elasticsearch's limits.

**Alternatives.** One document per definition, keyed by name: queryable, and a create can use
`op_type=create` for uniqueness, but a request touching several definitions needs a hand-written
rollback when one write fails, and other processes see half a change. A changes log of operations,
replayed at start-up: atomic per entry, but every process replays the whole history and compaction is
extra work.

**Consequences.** The document's size grows with the number of types; a deployment with tens of
thousands of custom types would revisit this. Type changes are serialised across the cluster, as
Atlas serialises them with its update lock.

### DD-029. Server processes share the type definitions through the document's version

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** Each process remembers the `_seq_no` and `_primary_term` of the `typedefs` document its
registry was built from. Before a type change it reloads when the stored document is newer; it then
writes conditionally on what it read. A conflict means another process changed types first: the process
reloads, applies the change again on the new definitions, and gives up with
`FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` after a second conflict. Readers reload when the document changed,
checked at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS` (default 5).

**Reason.** Atlas runs one active server and keeps its registry in memory (DD-024 is per process).
Several processes behind a load balancer must not lose each other's changes, and a change must reach the
others without a restart. Optimistic concurrency on one document gives both with one cheap `GET` of
the document's version.

**Alternatives.** A lock document: needs expiry and recovery when its holder dies. Change notification
through a message bus: a component the system does not have (ADR 050).

**Consequences.** For up to the refresh interval, a process may answer from older types than another;
a type change is visible at once only on the process that made it. 6.4 measures whether the interval
needs tuning.

### DD-030. The store asks the entity store whether a type is in use

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** The typedef store takes a `TypeUsage` callback that answers whether entities,
classifications or relationships of a type exist; deleting a type that is in use fails with
`TYPE_HAS_REFERENCES`. Until the entity store exists (2.2) the callback answers "not in use".

**Reason.** Atlas checks `typeHasInstanceVertex` before deleting a type. The instances live in the
entity store, which the typedef store must not depend on; a callback keeps the dependency pointing from
core's entity store to the typedef store.

**Alternatives.** Query the entity index from the typedef store: couples it to an index that does not
exist yet.

**Consequences.** 2.2 passes its own check when it builds the stores.

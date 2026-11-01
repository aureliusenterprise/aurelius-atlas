# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-023. Atlas errors live in the model library

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `AtlasErrorCode` and `AtlasError` move from `aurelius_atlas_server.errors` to
`aurelius_atlas_model.errors`. Each code keeps Atlas's HTTP status, error code and message template.
The server keeps the error handler and the response class and imports the errors from there.

**Reason.** The type system (1.2) and the stores raise Atlas errors, and they may not depend on the
server (DD-002: model ← typesystem ← core; server → core). In Java, too, `AtlasErrorCode` sits in
`intg`, below everything else.

**Alternatives.** A separate errors library: one more project for two classes. Each layer with its own
exception, mapped in the server: the mapping would repeat Atlas's error table.

**Consequences.** New error codes are added to `aurelius_atlas_model.errors` as each increment needs
them, copied from `AtlasErrorCode`.

### DD-024. The registry is updated on a transient copy under a re-entrant lock

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `TypeRegistry.lock_for_update(timeout)` returns a `TransientTypeRegistry` built from the
registry's definitions, under a re-entrant `threading.RLock`. Changes resolve every type on the copy;
`release(transient, commit=...)` swaps the copy's types into the registry or drops them. A context
manager wraps the pair.

**Reason.** It is Atlas's `TypeRegistryUpdateSynchronizer`: readers never see a half-resolved registry,
and a failed change leaves the registry as it was (TRG-05, TRG-09). A thread lock also protects
FastAPI's thread-pool handlers; async handlers hold it only around synchronous code.

**Alternatives.** An `asyncio.Lock`: does not protect code run in threads. Copy-on-write without a lock:
two concurrent updates would each start from the same registry and one would be lost.

**Consequences.** The lock is per process. Several server processes keep their registries in step
through the store (1.4).

### DD-025. The type system ports the definition side only

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** The ported types resolve definitions: names, attribute types, cardinalities, constraints
and later the hierarchies (1.3). Their value side (`isValidValue`, `getNormalizedValue`,
`validateValue`, `createDefaultValue`, `areEqualValues`) is ported with entity validation in 2.1. Their
JanusGraph side (vertex property names, unique property names, index field names, index-query escaping)
is not ported.

**Reason.** Types REST (1.6) needs only the definition side; values first matter for entities (2.1),
which is where Atlas's tests for them can be run. The JanusGraph names have no meaning in
Elasticsearch: the index mapping is designed in 2.2.

**Alternatives.** Port each class whole: one increment several times the size limit, with value code
untested by any endpoint until 2.x.

**Consequences.** The type classes grow in 2.1. Atlas behaviour that depends on vertex property names
is designed again for Elasticsearch in 2.2 and recorded there.

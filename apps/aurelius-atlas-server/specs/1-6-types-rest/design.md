# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-034. Lists of type definitions are sorted by name

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** `GET /v2/types/typedefs` and `GET /v2/types/typedefs/headers` list the definitions of each kind
sorted by name, compared as Java's `String.compareTo`.

**Reason.** Atlas lists them in the iteration order of the `ConcurrentHashMap`s of its registry: deterministic,
but a function of Java's string hashes and the maps' resize history, which no client can rely on and no
scenario can state without computing it. A sorted list is stable across restarts, processes and updates, which
the order of the stored document is not: an update moves a definition to its end.

**Alternatives.** The order of the stored document: changes with every update. Emulating Java's hash order:
costly, and still not something a client could use.

**Consequences.** DV-09. A scenario that lists several definitions of a kind states them sorted by name.

### DD-035. Type scenarios create what they read and delete it at their end

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** Each types scenario creates the definitions it needs, all named `scenario_…`, and deletes them in
its last stage. Before the server e2e runs its scenarios, it deletes any `scenario_…` definition left in the
store by an earlier run that stopped half-way.

**Reason.** The in-process scenarios start each from an empty store, but the e2e runs them all against one
server on the persistent dev store, which `nx serve` uses too. Self-contained scenarios pass on both, in any
order, and a run never touches a developer's own types.

**Alternatives.** Deleting the typedef index before the e2e: also deletes the developer's types and makes the
server load the models again. A separate index per e2e run: needs an index-name setting that nothing else
needs.

**Consequences.** Scenario names must be unique across scenarios; a scenario's expectations cannot depend on
types another scenario creates.

### DD-036. Start-up loading tries a raced change again

- **Status:** Proposed
- **Increment:** 1.6 (a fix to 1.5's MDL-15)
- **Date:** 2026-10-19

**Decision.** When the typedef store gives up on a model file or patch with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK`
(two lost conditional writes, DD-029), the model loader makes the change again, up to ten times, before it
treats the file as failed or the patch as `FAILED`. The REST endpoints keep DD-029's single retry.

**Reason.** DD-033 assumed a process starting next to another loses at most once per change. CI showed
otherwise: two processes write a few hundred changes in near lockstep, and between one's reload and its retry
the other may write its next file, so it loses twice and skipped a model file. Every lost race is another
process's write, so trying again always makes progress, and a file or patch is never skipped for a race.

**Alternatives.** More retries in the store itself: also lengthens a REST request's wait under contention,
where Atlas answers `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` at once. No limit: a store that never stops changing
would hang start-up.

**Consequences.** DD-033's "may each retry once per change" becomes "until it wins, up to ten times". A
process that loses ten times in a row still reports the file or patch as failed, as Atlas does on a lock
failure.

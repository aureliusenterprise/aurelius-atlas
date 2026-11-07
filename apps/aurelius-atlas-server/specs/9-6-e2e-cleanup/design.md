# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-368. A session of the server's e2e suite records what its answers created and removes it at its end

- **Status:** Proposed
- **Increment:** 9.6
- **Date:** 2026-11-07

**Decision.** The writer's clients of the server's e2e suite carry a response hook. It records the entities
and types each successful write's answer says were created, for the whole session. At the session's end, the
entities are deleted and purged, then the types left are deleted, all through the server's own API.

**Reason.** DD-223 allows writes to the shared dev store when they are namespaced and self-cleaned. The
suites' writes were namespaced by run, but not cleaned. The scenarios read as Atlas's own tests do: a stage
that deletes an entity tests the delete, and adding a clean-up stage to each of the 59 scenarios would make
every scenario longer and still miss a scenario that fails midway. The answers already name what was created,
so one hook covers every scenario and test, whether it passes or fails. Removing by what was recorded, not by
name pattern, leaves a parallel run's writes alone.

**Alternatives.**

- A clean-up stage in every scenario: long, and skipped when an earlier stage fails.
- A sweep by name pattern, `scenario_*` and `e2e_*`: it would remove a parallel run's types mid-test.
- Each test cleaning its own writes in a `finally`, as the load test does: right for one test with one type,
  but it repeats per test and cannot reach into the scenario runner.

**Consequences.** A run leaves the dev store as it found it, except for the server's admin audits of the
purges and the entity audits of the removed entities, which Atlas keeps too. Leftovers from earlier runs
stay until they are removed once by hand. A write that creates something without naming it in its answer
needs its test to register it, as the replication test does for its `AtlasServer`.

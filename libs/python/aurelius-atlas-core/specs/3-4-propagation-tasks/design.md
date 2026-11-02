# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-079. Tasks are documents of their own index, written with the change that records them

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** A task is one document of the index behind `aurelius-atlas-tasks`, keyed by its GUID: Atlas's
task fields and the claim of DD-080. The entity it is queued on lists its GUID in `pendingTasks` (a
relationship update's task, the relationship). A task is written in the write of the change that records it,
as relationships and classification instances are (DD-062, DD-071), and journaled with it.

**Reason.** Atlas creates the task vertex in the request's graph transaction: a change and its task commit
together or not at all.

**Alternatives.** Queuing tasks after the write: a crash in between loses the propagation.

**Consequences.** `EntityStore.write` takes task changes as a third kind of listed document.

### DD-080. Every server process runs tasks, each claimed with a lease

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** Each server process runs a worker that takes `PENDING` tasks oldest first. It claims one by
writing it `IN_PROGRESS`, with its start time and a claim lease, conditionally on the version it read; a claim
another process won is skipped. A task claimed by a process that stopped is taken over once its lease has
passed. A request that records tasks wakes its own process's worker; the workers also look for tasks at an
interval.

**Reason.** Several processes may share one store; the conditional claim lets any run any task exactly once at
a time, without electing a leader, and a stopped process's tasks are resumed.

**Alternatives.** One worker on an elected leader, as Atlas's active instance: leader election and takeover to
build for no gain in correctness.

**Consequences.** Tasks of different entities may run side by side in different processes (DV-38).

### DD-081. Tasks are enabled by a server setting, on by default

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** `AURELIUS_ATLAS_SERVER_TASKS_ENABLED` (default `true`, Atlas's `atlas.tasks.enabled`) chooses
whether propagation is deferred to tasks; `false` keeps 3.4a's propagation within the request.

**Reason.** Atlas's default defers it; the setting keeps the synchronous form for deployments and tests that
want a write to be complete when it answers.

**Alternatives.** Always deferred: no way to have a propagation done when its request answers.

**Consequences.** The core takes the choice as a parameter of the writers and stores that propagate. The parity
scenarios run against a server with tasks disabled, as against an Atlas with `atlas.tasks.enabled=false`: they
check what propagation produces, not when, and `admin/session` reports the setting.

# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-075. A propagated classification is listed by the entities it reaches

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** An entity a classification is propagated to lists the instance's GUID in its
`classificationGuids`, after its own, as its entity does; an instance listed by an entity other than its
`entityGuid` is propagated to it. Atlas's propagated `classifiedAs` edge is this listing.

**Reason.** One instance stays one document (DD-070): an update of it reaches every entity listing it at once,
as in Atlas, and an entity's reads stay gets by id.

**Alternatives.** A copy of the classification per entity reached: every change rewrites every copy.

**Consequences.** A classification propagated far makes many entity documents change in one write (DD-071),
and writers relating those entities conflict more (DV-30).

### DD-076. The entities a classification reached are found through an indexed field

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** `classificationGuids` is indexed; the entities listing an instance are found by searching it
after a refresh, page by page, as DD-057 finds referring entities, and checked against the request's own
changes.

**Reason.** Removing a propagation needs the entities a classification reached (`getPropagatedEdges`); a
search keeps the classification's document small however far it propagates.

**Alternatives.** The instance listing the entities it reached: exact and real time, but as large as its
reach, and rewritten on every change of it.

**Consequences.** A search may miss an entity a concurrent write has just made list the instance, as DV-27
says for references.

### DD-077. Propagation runs within the request until 3.4b

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** In 3.4a, the request that causes a propagation computes and writes it, as Atlas does with
`atlas.tasks.enabled=false`; 3.4b defers it to tasks, Atlas's default.

**Reason.** The propagation itself is the same either way; deferring it is a second, separable concern with
its own queue, worker and endpoints.

**Alternatives.** Tasks from the start: one increment far above the size limit.

**Consequences.** Until 3.4b a request that propagates far takes as long as its propagation, and entities have
no `pendingTasks`.

### DD-078. 3.4 is split into propagation and propagation tasks

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** 3.4a ports propagation and its triggers, run within the request (DD-077); 3.4b ports the
deferred tasks: the task index and worker, `pendingTasks`, `admin/tasks` and the checks of pending tasks.

**Reason.** Together they are above the size an increment may have (ADR 051).

**Alternatives.** One increment.

**Consequences.** 3.4b changes when propagation runs, not what it does.

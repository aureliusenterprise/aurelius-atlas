# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-318. Stored metrics are entities, deleted softly, listed without the deleted ones

- **Status:** Proposed
- **Increment:** 6.4b
- **Date:** 2026-11-04

**Decision.** A stored metric is a `__AtlasMetricsStat` entity written through `DataAccess`, as the server
records are (DD-307): stored and purged unchecked, read as the request's user. A purge deletes it as an entity
delete does, so it stays as `DELETED`. The list takes the entities of the type, leaves out the deleted ones by
their stored state, and loads the rest.

**Reason.** Atlas stores and deletes them through its `DataAccess` too, so a purged metric remains as a deleted
vertex, and its list loads every GUID of the type and drops the deleted ones as they fail to load. Leaving the
deleted ones out before loading gives the same list without reading them: at 24 a day, they soon outnumber the
336 kept.

**Alternatives.** Purging them for good: no deleted ones to skip, but a write the entity store keeps for
`admin/purge`, and an observable difference from Atlas. A document kind of their own: no entity at all, but
`__AtlasMetricsStat` is in the base model and its entities are searchable in Atlas.

**Consequences.** The deleted metrics grow by one an hour per server process, as in Atlas; `admin/purge` removes
them.

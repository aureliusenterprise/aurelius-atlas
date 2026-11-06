# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-318. Stored metrics are entities, deleted softly, listed without the deleted ones

- **Status:** Proposed
- **Increment:** 6.4b
- **Date:** 2026-11-04

**Decision.** A stored metric is a `__AtlasMetricsStat` entity written through `DataAccess`, as the server
records are (DD-307): stored and purged unchecked, read as the request's user. A purge deletes it as an entity
delete does, so it stays as `DELETED`. The list takes the entities of the type, leaves out the deleted ones by
their stored state, and loads the rest.

**Reason.** Atlas stores and deletes them through its `DataAccess` too, so a purged metric remains as a
deleted vertex, and its list loads every GUID of the type and drops the deleted ones as they fail to load.
Leaving the deleted ones out before loading gives the same list without reading them: at 24 a day, they soon
outnumber the 336 kept.

**Alternatives.** Purging them for good: no deleted ones to skip, but a write the entity store keeps for
`admin/purge`, and an observable difference from Atlas. A document kind of their own: no entity at all, but
`__AtlasMetricsStat` is in the base model and its entities are searchable in Atlas.

**Consequences.** The deleted metrics grow by one an hour per server process, as in Atlas; `admin/purge`
removes them.

### DD-365. The Statistics chart starts with every entity type, summed by the server

- **Status:** Proposed
- **Increment:** 6.4b (a change asked for on the dashboards)
- **Date:** 2026-11-06

**Decision.** `_ALL_ENTITY_TYPES`, as a chart's or a range's type name, reads the sum over every entity type's
own count, per snapshot and state. The vendored dashboards' Statistics chart starts with that name instead of
`hive_table` (`PATCHES.md`, patch 02). Clicking a type in the Entities table charts that type, as before.

**Reason.** The dashboards hard-code `hive_table` as the chart's first type. A catalogue without Hive, which
this one is, opens the chart on nothing. The name is the one the dashboards already use for every entity type
in search, so it reads the same in both places. Summing on the server keeps the request one name long; summing
in the browser would ask for every type by name, hundreds of them.

**Alternatives.** Asking for each type in the browser and summing there: a long URL and a larger patch.
Changing only the default to a type the catalogue has: still one type, and the catalogue decides which.

**Consequences.** Atlas answers `_ALL_ENTITY_TYPES` as an unknown type with zero counts (DV-141). The chart's
title shows the name as it is, `_ALL_ENTITY_TYPES chart for last 7 days`.

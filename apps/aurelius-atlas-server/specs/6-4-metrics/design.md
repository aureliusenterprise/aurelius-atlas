# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-317. The metrics count the entities in one composite aggregation

- **Status:** Proposed
- **Increment:** 6.4a
- **Date:** 2026-11-04

**Decision.** The entity documents answer `type_counts`: a `composite` aggregation of the entity index by
`typeName`, `state` and `isIncomplete`, paged by 1,000 buckets. The classification index is counted by `typeName`
the same way. `MetricsService` folds the buckets into the active, deleted and shell counts per type and sums them
over each type's sub types. One health check of the store answers both `statusBackendStore` and
`statusIndexStore`.

**Reason.** Atlas runs three index queries per entity type and one per classification type, so a catalogue of
a few hundred types costs a thousand round trips for one `admin/metrics`. A composite aggregation answers every
type in a few pages, and a bucket per type, state and flag gives the three counts at once. Unlike a `terms`
aggregation, it pages, so no type is cut off. Elasticsearch is both Atlas's graph backend and its index here;
the health check that answers readiness (ADM-04) is the one test of either.

**Alternatives.** A `count` per type and state, as Atlas does: faithful, but the cost grows with the types. The
search facets (DD-093): capped at 100 values, so a larger catalogue would lose types.

**Consequences.** The counts are as of the last refresh, which every write makes (ENS-11). The fake client
answers `composite` aggregations for the unit tests.

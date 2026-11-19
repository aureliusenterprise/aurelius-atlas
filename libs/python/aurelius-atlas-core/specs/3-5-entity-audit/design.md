# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-082. Audit events are documents of their own index, written after the change

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** Increment 3.5 is split: 3.5a records the events of entity writes, deletes and purges and answers
`{guid}/audit`; 3.5b adds the classification events and `bulk/headers`. An audit event is one document of the
index behind `aurelius-atlas-entity-audits`. The events of a change are written once the change has committed,
from the entities read back, in one bulk request; they are not part of the change's journaled write.

**Reason.** Atlas keeps its audit in HBase, apart from the graph, and writes it in the request before the
graph commits; neither store's write includes the other's. Reading the committed entities gives the details
exactly as a later read answers them, without computing them from a request's view in every writer.

**Alternatives.** Events as a further kind of document in the journaled write (DD-079): no event lost, but
each writer would compute the details before its write.

**Consequences.** A process that stops between the write and its events loses them (DV-40).

### DD-083. Audit events keep Atlas's event keys and their order

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** An event's `eventKey` is the HBase row key Atlas writes, `<entityId>:<timestamp>:<index>:<now>`,
a keyword of the event's document. Events are read newest first by sorting on it descending, as Atlas's
reversed HBase scan reads them; `startKey` is a bound on it. The document's id is a new GUID, so two events
with one key are both kept.

**Reason.** Keyword order is the byte order HBase sorts row keys in, so the order and the `startKey` paging
the dashboards and clients rely on stay Atlas's, quirks included.

**Alternatives.** Sorting by timestamp: events of one millisecond would come in another order, and `startKey`
would need a translation.

**Consequences.** Where HBase would overwrite an event whose key repeats, both events are listed.

### DD-084. The entity writer tells a change notifier what it changed

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** `EntityWriter` takes an optional `EntityChangeNotifier`, Atlas's `AtlasEntityChangeNotifier`,
and gives it each committed response with the request's user. The notifier prunes the response and calls its
listeners; the audit listener is the only one. Without a notifier nothing is recorded.

**Reason.** Atlas's entity store notifies after every mutation; one hook in the writer covers creates,
updates, deletes and purges, and tests of the writer need no audit.

**Alternatives.** The server recording events after each route: every route would repeat it, and core callers
would record nothing.

**Consequences.** 3.5b gives the classification operations the same notifier. The writer prunes every response
as `pruneResponse` does, also without a notifier, since Atlas answers the response it pruned: an entity listed
as deleted is no longer also listed as updated (OWN-03).

### DD-710. The sorted audit listing sorts in Elasticsearch, on folded keys

- **Status:** Proposed
- **Increment:** 3.5 (a fix, 2026-11-19)
- **Date:** 2026-11-19

**Decision.** `listEventsV2` with a sort column asks Elasticsearch for the order instead of reading the entity
whole and sorting in memory (AUD-07). Each event stores two keyword fields beside `user` and `action`: `userKey`
and `actionKey`, each the fold of its column (every character upper-cased, then lower-cased). A sort on `user`
sorts on `userKey` then `timestamp`, one on `action` on `actionKey` then `timestamp`, and any other column on
`timestamp`, with `eventKey` and `auditId` descending as the last keys in both directions. `prepare` gives both
fields to an index that predates them and rewrites the events still without them.

**Reason.** Java's `HBaseBasedAuditRepository.listEventsV2` reads the entity's events and sorts them with
`EntityAuditEventV2.sortEvents`, which costs a full scan per request. The store answers the same order for the
cost of a sorted search. Elasticsearch has no case-insensitive field sort (only the query-time
`case_insensitive` on term-level queries), so the fold lives in the document. It is the same fold the ported
`sort_events` uses, which gives a null user or action the empty fold: first ascending, last descending. The tail
breaks ties by newest key first, descending in both directions, because Java's sort is stable over the
newest-key-first scan.

**Alternatives.** Keep Java's in-memory sort (3.5 as written): exact parity, but every paged read pays the whole
scan. A case-folding normalizer on the store's analyzer: changing analysis settings needs the index closed, which
the server cannot do while it answers reads, and the fold would leak into the term listings of AUD-08. A runtime
field or script sort: Elasticsearch computes it per hit and the fake store does not run scripts.

**Consequences.** Events stored before the fold sort as the empty fold until the next `prepare` rewrites them.
`sort_events` stays for the in-memory repository and the aging, which read their events whole anyway. The route,
the response and the rule text of AUD-07 do not change.

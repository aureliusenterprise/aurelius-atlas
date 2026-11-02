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

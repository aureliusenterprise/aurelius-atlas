# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-303. An export walks the stored relationships and references for Atlas's Gremlin edges

- **Status:** Proposed
- **Increment:** 6.3a
- **Date:** 2026-11-02

**Decision.** What Atlas's export finds with Gremlin is found from the stored documents. The starting entities
of a type, or of a type holding a value, are read by scanning the entities of exactly that type (`of_types`)
and testing their stored values. An entity's edges are its relationships, outward from end 1, in any state
(DD-061), and its references, outward from the referring entity, found back through `referring` (DD-057).

**Reason.** Atlas's `bothE`, `inE` and `outE` walk every edge of the entity vertex. In Atlas 2.4 those are the
relationship edges, created from end 1 to end 2, and the edges of references that have no relationship type.
Our store keeps both, so the walk gives the same entities. Atlas's value matches (`startsWith` and the like)
filter every vertex of the type in Groovy rather than use an index, so a scan of the type is the same work.

**Alternatives.** New search fields for every attribute value: an index for a query that runs rarely, and
`matches` would still need a scan.

**Consequences.** An export of a large type reads all of its documents. Lineage is kept for a second round,
as Atlas's queues do.

### DD-304. One export or import at a time per server process, the ZIP built in memory

- **Status:** Proposed
- **Increment:** 6.3a
- **Date:** 2026-11-02

**Decision.** The lock that keeps a second export or import out is an `asyncio.Lock` of the server process. The
export's ZIP is written into memory and answered once complete.

**Reason.** Atlas's lock is a `ReentrantLock` of its single active server; a process-wide lock keeps that rule
for one server. Building the ZIP before answering lets a failure answer an error, not a cut-off download.

**Alternatives.** A lock in Elasticsearch, shared by every replica: needed only when several replicas export
at once, and it must survive a crashed holder. Streaming the ZIP: less memory, but a failure halfway leaves the
client with a broken file and a 200.

**Consequences.** Two replicas behind one service can each run an export. An export's size is bounded by the
server's memory.

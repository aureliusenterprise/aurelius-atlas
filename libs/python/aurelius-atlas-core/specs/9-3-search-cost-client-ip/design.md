# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-237. Index refresh moves from reads to writes

- **Status:** Accepted
- **Increment:** 9.3
- **Date:** 2026-10-28

**Decision.** Every write a search reads carries `refresh="wait_for"`:
the entity/linked bulk (`EntityDocuments.write`), the entity restore, the
linked restore, the journal put and delete, and the audit append
(`put_events`). No read path calls `indices.refresh` — `count_type`,
`referring`, `classified`, `search`, `terms`, `journal`, `list_tasks`,
`count_linked_type`, `classifications_of_types`, `list_events`,
`entities_with_tag_changes` all lose theirs. Reservations stay unrefreshed:
they are read by `mget`, which is real time (ENS-04). `wait_for` (not `true`)
also waits for the _concurrent_ writes' refresh — the pair that keeps a
reader from seeing half of one bulk (DV-16's shape, unchanged). ENS-11.

**Reason.** Pentest M6: every read paid a full index refresh on the request's
critical path — a search, a count, an audit listing each forced a refresh of
the entities (or audits) index. That is a denial-of-service lever on the
store, not a feature: `refresh` is a write-path affordance, and Apache Atlas
refreshes nothing on reads (JanusGraph's transactional graph cache makes it
pointless there). Read-your-writes (ENS-04, ENS-07's visible contract) needs
the refresh _once_, at the write that created the fact; paying for it on
every reader multiplies the cost by the read:write ratio.

**Alternatives.** (a) `refresh=true` — refused: it forces a refresh of every
shard immediately and serialises concurrent writers on it; `wait_for` joins
the refresh the write's own request triggers. (b) Refresh only on the writes
that mutate what the UI searches (bulk, restore) and leave journal/audit on
reads — refused: the journal read is recovery's (a restart reads entries
written moments before), the audit list rides the audit append; a partial
move re-introduces the read-side cost on the paths kept. (c) No refresh at
all, tolerate stale reads — refused: ENS-04's read-your-writes is
scenario-pinned (write → search returns the entity), and Atlas's
transactional visibility is the parity behaviour. (d) A `searchRequestCache`
-style read-your-writes (ES's real-time GETs + `search_after` on `seq_no`):
ES's `mget`-real-time + `wait_for`-refresh pair is the same guarantee with
less machinery.

**Consequences.** Write latency rises (the response waits for the refresh);
read latency falls off a cliff at the p99. The fake client records the
`refresh` kwarg of every write (`write_refreshes`) and keeps counting
`indices.refresh` calls (`refreshes`), so the unit tests pin both halves:
writes carry `wait_for`, reads call refresh never. The e2e parity scenarios
(write → search sequences) are the acceptance over the real store — they
stay green unchanged, which _is_ the read-your-writes proof. Supersedes the
read-side refresh rationale in DD-043, DD-048, DD-057 (their decisions
stand; only the refresh's location moves). Next free DD: 238.

# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-322. A write refreshes what it wrote

- **Status:** Proposed
- **Increment:** 6.4d
- **Date:** 2026-11-04
- **Supersedes:** [DD-237](../../../../libs/python/aurelius-atlas-core/specs/9-3-search-cost-client-ip/design.md#dd-237-index-refresh-moves-from-reads-to-writes)'s
  choice of `wait_for`; the rest of DD-237 stands

**Decision.** The writes that DD-237 gave `refresh="wait_for"` carry `refresh="true"`: Elasticsearch refreshes
the shards the write touched, then answers. Reads still refresh nothing.

**Reason.** `wait_for` answers at the index's next scheduled refresh, once a second by default, and a shard
that no search has touched for a while skips its scheduled refreshes. On the dev store one write waited
720 ms, and two in a row 1.3 s; a create is two (the entity, then its audit), an update more. With `true` one
write takes 13 ms. Under the 6.4c load test, 8 users for 20 seconds, a create's median fell from 1,018 to
202 ms, and the run served three times as many requests. DD-237 refused `true` because it "serialises
concurrent writers" on the refresh; the load test measures that cost, and it is a fifth of the wait it
replaces.

**Alternatives.** A shorter `refresh_interval` with `wait_for`: at 250 ms a write still waited 223 ms, and every
index refreshes four times a second whether written or not. No refresh at all: loses read-your-writes, which
DD-237 keeps for Atlas parity.

**Consequences.** Each write makes a small segment, which Elasticsearch merges in the background; at a
catalogue's write rates that is cheap. A bulk import refreshes once per bulk, not per entity. A search's 95th
percentile under load rose from 68 to 205 ms, because three times as many writes ran beside it.

### DD-323. The indices expand their replicas to the cluster

- **Status:** Proposed
- **Increment:** 6.4d
- **Date:** 2026-11-04

**Decision.** Every index the server creates has `index.auto_expand_replicas: 0-1`, and the server puts the
setting on an index that exists when it prepares it.

**Reason.** Each index asked for Elasticsearch's default of one replica. Dev and the chart run one node, which
cannot hold a replica beside its primary, so every index was yellow forever and the store's health could only
say red or not. With the setting a single node has no replica and is green; a second node gets one.

**Alternatives.** `number_of_replicas: 0`: green on one node, but a cluster that grows keeps no copy. A
replica count in the server's settings: one more setting to keep equal to the cluster, which the cluster
already knows.

**Consequences.** On one node an index has no copy, as before in effect: a replica nobody could place protected
nothing. A yellow store now means something is wrong, which the alert of 6.4c can be tightened to say.

### DD-324. Each lifetime lives in its tool's own configuration, and one page states them all

- **Status:** Proposed
- **Increment:** 6.4d
- **Date:** 2026-11-04

**Decision.** Each store's lifetime is set where its tool reads it: Prometheus's flag, Loki's compactor, Tempo's
override, Grafana's env, the realm's import, the server's aging settings. Dev and the chart state the same
value, and the chart suite holds them equal. The Data Archiving page names every kind with its lifetime, and a
test fails when a dev volume has no row there.

**Reason.** A lifetime a person cannot find is no answer to ADR 025's "how long do we keep X?". A lifetime set
in a wrapper the tool does not read is one more thing to drift. The tools' own settings are what enforces the
period; the page is where a person reads it; the test keeps a new store from arriving undeclared (R6).

**Alternatives.** One lifetimes file rendered into each tool's configuration: one place to change, but a
generator between every config and its tool, in dev and in the chart. Elasticsearch index lifecycle
policies for the audits: the aging of 6.3c4 is Atlas's own mechanism, by entity and action, which a policy by
index age cannot express.

**Consequences.** A change to a period touches the tool's config, its chart copy and the page, in one reviewed
change. The page is checked for its volumes, not its periods: a period changed in a config but not on the page
is caught in review.

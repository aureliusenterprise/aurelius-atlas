# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-367. The standalone stack keeps its catalogue in an Elasticsearch of its own

- **Status:** Proposed
- **Increment:** 9.5c
- **Date:** 2026-11-06
- **Supersedes:** none; DD-363 placed the stack on the dev store without a decision of its own

**Decision.** The standalone stack runs one Elasticsearch node of its own, with its own volumes and no
published port, configured and certified as `dev/elasticsearch` is. The server reaches only that store, and
the stack no longer joins the dev store's network.

**Reason.** The dev store is shared: `nx serve` and the e2e suites write to the same indices (DD-223). The
suites name their types and entities by run and leave them behind. A deleted entity stays `DELETED`, and a
type is never removed. On the dev store, the stack's dashboards listed about 330 types of test runs beside
the sample data. A store of its own shows only what was imported, and `down -v` returns it to empty.

**Alternatives.**

- An index prefix for the server inside the dev store: the entity store takes a prefix already, but the
  server exposes none, and the audit and other stores have their names fixed. That is a change across the
  libraries for what a compose file gives.
- Clearing the dev store: the next e2e run fills it again, and it removes what `nx serve` keeps there.
- The suites cleaning up after themselves: deleted entities and unused types would still have to be purged,
  and a run that fails midway would leave its share anyway.

**Consequences.** The stack takes one more node, about 2 GB of memory at its cap, and starts without the dev
store. It reads `dev/elasticsearch/certs/`, which `nx certgen aurelius-atlas-dev-elasticsearch` makes on a
new clone. A new store's Statistics chart is empty until its first hourly snapshot.

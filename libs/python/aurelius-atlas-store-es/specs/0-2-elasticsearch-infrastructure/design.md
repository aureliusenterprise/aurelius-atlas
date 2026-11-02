# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-005. The store uses the official async Elasticsearch client

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-store-es` talks to Elasticsearch through `AsyncElasticsearch` from the
official `elasticsearch` Python client, version 9.5 or later within major 9, matching the 9.5 server
(`dhi.io/elasticsearch:9.5-debian13`; minor upgrades are deliberate, patch releases follow the tag). A
store instance owns exactly one client, opened and closed with the store (`async with`).

**Reason.** The server is FastAPI and asynchronous; a blocking client would tie up the event loop or
need a thread pool. The official client tracks the server's API and versioning, ships typed
request helpers, and includes the query DSL module that search (4.x) will need.

**Alternatives.** `httpx` against the REST API directly: no extra dependency, but every API, retry
and error type would be rebuilt by hand. `opensearch-py`: a different server; ADR 047 names
Elasticsearch. One client per request: simple, but loses connection pooling.

**Consequences.** The client's major version moves with the server's (STO-04 guards it). Connection
pooling and retries are the client's; tuning them is part of 6.4.

### DD-007. The Elasticsearch test fixture ships with the store library

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The testcontainers helper that starts a TLS-enabled Elasticsearch lives in
`aurelius_atlas_store_es.testing`, behind the library's `testing` extra, next to the code it serves.

**Reason.** Every later project with a store (`-core`, the server, the parity harness) needs the same
container; the library that defines the settings is the one that knows how to build them for a test
server, and keeping both together means a settings change cannot break the fixture unnoticed.

**Alternatives.** `aurelius-atlas-sdk.testing`, where the Postgres helper lives: would make the
generic SDK depend on Elasticsearch. A copy per project: drifts.

**Consequences.** Test-only dependencies (`testcontainers`, `trustme`) stay out of the runtime install;
consuming projects add `aurelius-atlas-store-es[testing]` to their dev dependencies.

### DD-008. A yellow cluster is healthy

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The store's health check reports up for cluster status green or yellow and down for red
(STO-05).

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only
replicas are missing. A single-node cluster, the development and small-installation case
([ADR 006][a006]), is yellow as soon as an index has a
replica. Reporting it down would make every single-node deployment permanently unready.

**Alternatives.** Green only: correct for multi-node clusters, unusable for single-node ones unless
every index is created with zero replicas. A configurable threshold: one more setting nobody sets.

**Consequences.** Lost redundancy is not visible as a health failure; it is visible in the cluster
metrics (ESD-06) and should be alerted on there.

[a006]: ../../../../../docs/architecture/adr/006-the-whole-system-runs-on-one-machine.md

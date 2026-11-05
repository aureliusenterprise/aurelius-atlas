# 9.3 Search cost and client-IP trust

- **Status:** done
- **Pull request:** [#155](https://github.com/aureliusenterprise/aurelius-atlas/pull/155)
- **Records:** DD-237, DD-238; supersedes the read-side refresh rationale in DD-043, DD-048 and DD-057

This page is the `aurelius-atlas-core` part of increment 9.3; its rule table is
the increment's shared set. The other part is with [`aurelius-atlas-server`][part-0].

## Scope

The pentest's search-cost finding (M6) and the client-IP trust gap (L3), one increment on the
core library, the server and the webapp's nginx edge:

- **Refresh moves to writes** (ENS-11, [DD-237](design.md#dd-237-index-refresh-moves-from-reads-to-writes)):
  every write carries `refresh="wait_for"` and the read paths stop calling `indices.refresh` —
  today every search, count, listing and audit read pays a full index refresh on the request's
  critical path, which is a denial-of-service lever, not a feature.
  Not in scope:

| Not delivered here                                                     | Delivered by                |
| ---------------------------------------------------------------------- | --------------------------- |
| Authentication (every bucket is per-IP until then)                     | 6.1 (separate PR track)     |
| CSRF enforcement                                                       | the CSRF increment (ADM-06) |
| Per-user / per-token rate limits                                       | with 6.1's identity         |
| Elasticsearch-side throttling (`search.max_concurrent_shard_requests`) | not planned                 |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ENS-11 | A write makes its documents visible to the next read: the bulk and every single-document write a search reads (entity restore, journal write and delete, linked restore, audit append) carry `refresh="true"` (`"wait_for"` until 6.4d, DD-322), and no read path calls `indices.refresh`. Reservations need none — they are read by `mget`, real time as ENS-04 says of entities. A write's response is sent after the refresh, so a reader never sees a partially visible write (ENS-07's "a reader may see part of a write while it is being written" is unchanged).                                                                                                                                                                                             |
| SRV-09 | **Retired as an e2e rule (DD-281); the shipped limiter config stays.** Was: the webapp's nginx `/api/` proxy carries a `limit_req` zone keyed on the client address (300r/m, burst 100, `nodelay`; refusals answered 429, nginx's default 503 overridden). The key is a `geo`/`map` pair: private ranges (RFC 1918, loopback) map to the empty key, which nginx does not account — internal callers and dev/e2e traffic pass unlimited, browsers are limited. The refusal is nginx's own 429 (an HTML body, no Atlas error body, no `Retry-After` — `limit_req` sends none): the server carries no limiter and answers every request it receives. The shipped template and its chart-render guards remain (DV-87 stands); only the live-flood e2e proof is retired. |
| SRV-10 | `forwarded_allow_ips` is passed to uvicorn, declaring which peers may rewrite the client address through `X-Forwarded-For` (default `127.0.0.1`); the dev/e2e compose arrangements name the proxy network, so the access log and OTel peer attributes key on the browser's address, not the proxy's.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## Java origin

Apache Atlas 2.4.0 refreshes nothing on reads (JanusGraph's graph cache is transactional) and ships
no rate limiter — both rules are Aurelius-side hardening, not parity ports. Neither touches the
wire shape the scenarios pin: ENS-11 keeps read-your-writes, and a 429 is a refusal nginx answers
before a request reaches the Atlas-shaped surface.

## Deviations

- [DV-87](../../../../../docs/architecture/conversion/deviations.md) : a rate-limited request answers 429;
  Atlas has no limiter and answers every request. The limit sits at the webapp's nginx edge, so a caller that
  reaches the server directly (internal apps, deployments without the webapp) sees Atlas's answer-everything
  behaviour; the webapp arrangement is the browser's front door, and that one is limited.

ENS-11 keeps the visible behaviour (read-your-writes, ENS-04/ENS-07) — only its cost moves
from every read to every write.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_documents.py`,
  `test__entity_audit_repository.py` — the fake records the `refresh` kwarg of every bulk and
  single-document write; the tests name the write paths and assert `wait_for`, and the read
  tests assert no `indices.refresh` call (ENS-11).
- `nx e2e aurelius-atlas-server` — the parity scenarios (write → search stage sequences) stay
  green unchanged: that is the read-your-writes acceptance, over the real store.

[part-0]: ../../../../../apps/aurelius-atlas-server/specs/9-3-search-cost-client-ip/spec.md

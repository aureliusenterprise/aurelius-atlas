# 9.3 Search cost and client-IP trust

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-237, DD-238; supersedes the read-side refresh rationale in DD-043, DD-048 and DD-057

## Scope

The pentest's search-cost finding (M6) and the client-IP trust gap (L3), one increment on the
core library and the server:

- **Refresh moves to writes** (ENS-11, [DD-237](../design-log.md#dd-237--index-refresh-moves-from-reads-to-writes)):
  every write carries `refresh="wait_for"` and the read paths stop calling `indices.refresh` —
  today every search, count, listing and audit read pays a full index refresh on the request's
  critical path, which is a denial-of-service lever, not a feature.
- **Rate limit on the mutating and search routes** (SRV-09, [DD-238](../design-log.md#dd-238--a-token-bucket-rates-the-write-and-search-routes-per-client-ip)):
  a pure-ASGI token bucket keyed on the client IP, sized for interactive use, off by default so
  tests and non-browser callers are unaffected.
- **Client-IP trust** (SRV-10, same DD): uvicorn's `forwarded_allow_ips` becomes a setting so the
  proxy hop is declared, `scope["client"]` is the browser, and the limiter (and the access log,
  and OTel's peer attributes) key on the real client.

Not in scope:

| Not delivered here                                                     | Delivered by                |
| ---------------------------------------------------------------------- | --------------------------- |
| Authentication (every bucket is per-IP until then)                     | 6.1 (separate PR track)     |
| CSRF enforcement                                                       | the CSRF increment (ADM-06) |
| Per-user / per-token rate limits                                       | with 6.1's identity         |
| Elasticsearch-side throttling (`search.max_concurrent_shard_requests`) | not planned                 |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ENS-11 | A write makes its documents visible to the next read: the bulk and the single-document writes (restore, reserve, journal, linked writes, audit append) carry `refresh="wait_for"`, and no read path calls `indices.refresh`. A write's response is sent after the refresh, so a reader never sees a partially visible write (ENS-07's "a reader may see part of a write while it is being written" is unchanged). |
| SRV-09 | `rate_limit_per_minute` (0 = off, the default) gives each client IP a token bucket of that many requests per minute over `POST /api/atlas/v2/entity*`, `POST /api/atlas/v2/search/*` and `DELETE /api/atlas/v2/entity*`; over the limit answers 429 with SRV-04's Atlas error body — a new code (`ATLAS-429-00-001`; Atlas has no 429, so it follows Atlas's format) — and a `Retry-After` header.                |
| SRV-10 | `forwarded_allow_ips` is passed to uvicorn, declaring which peers may rewrite the client address through `X-Forwarded-For` (default `127.0.0.1`); the dev/e2e compose arrangements name the proxy network, so the limiter, the access log and OTel peer attributes key on the browser's address, not the proxy's.                                                                                                 |

## Java origin

Apache Atlas 2.4.0 refreshes nothing on reads (JanusGraph's graph cache is transactional) and ships
no rate limiter — both rules are Aurelius-side hardening, not parity ports. The wire shape of the
429 follows Atlas's error body (SRV-04), which the scenarios already pin.

## Deviations

- [DV-87](../deviations.md): a rate-limited request answers 429; Atlas has no limiter and answers
  every request. With the default 0 (off) the shipped behaviour is Atlas's — the entry covers the
  enabled arrangement, and the code format follows Atlas's convention (no Java precedent).

ENS-11 keeps the visible behaviour (read-your-writes, ENS-04/ENS-07) — only its cost moves
from every read to every write.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_documents.py`,
  `test__entity_audit_repository.py` — the fake records the `refresh` kwarg of every bulk and
  single-document write; the tests name the write paths and assert `wait_for`, and the read
  tests assert no `indices.refresh` call (ENS-11).
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_rate_limit.py` — bucket fills,
  refills, per-IP isolation, `Retry-After`, off-by-default, 4xx on non-bucketed routes (SRV-09).
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server___main__.py` — uvicorn options
  carry `forwarded_allow_ips` (SRV-10).
- `nx e2e aurelius-atlas-server` — the parity scenarios (write → search stage sequences) stay
  green unchanged: that is the read-your-writes acceptance, over the real store.
- Manual (dev stack): repeated `POST search/basic` from the webapp shows the browser's IP in the
  server's access log, and the limiter's 429 after the configured burst.

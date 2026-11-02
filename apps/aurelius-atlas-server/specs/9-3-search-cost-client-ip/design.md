# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-238. The browser rate limit lives at the nginx edge, not in the server

- **Status:** Accepted
- **Increment:** 9.3
- **Date:** 2026-10-28

**Decision.** The webapp's nginx (`nginx.conf.template`, mirrored by
`e2e/config/nginx.conf`) carries a `limit_req` leaky bucket on the `/api/`
proxy: key `$binary_remote_addr` through a `geo`/`map` pair that maps the
private ranges (RFC 1918 + loopback) to the empty key — nginx does not
account requests with an empty key — `rate=300r/m`, `burst=100`, `nodelay`,
`limit_req_status 429`. The server itself has no limiter: no middleware,
no setting, no 429 error code in the enum. uvicorn's `forwarded_allow_ips`
becomes a server setting (default `127.0.0.1`) so the webapp proxy hop is
declared and the access log / OTel peer attributes key on the browser's
address, not the proxy's (SRV-10). The e2e bucket is test-sized (60r/m,
burst 20) so the burst test can outspend it sequentially. SRV-09.

**Reason.** Pentest M6's search-cost half: a browser (or a script posing as
one) can fire unbounded searches. The limit belongs where the browser is:
at the webapp edge, nginx already terminates TLS, proxies `/api/`, stamps
headers — the bucket is one more line of the same job, runs in C, shares
state across workers in one shm zone, and refuses before a request costs a
handler, a query, or an ES fan-out. The user's steer: internal apps are not
the concern — a service bursting the API is working, a browser flooding it
is attacking; the private-range allowlist is exactly that split. An
application-layer limiter (pure-ASGI token bucket; slowapi/limits) was
built and removed: it also limits the internal callers nobody worries
about, its limits are per-process (a multi-worker deployment multiplies the
budget), and uvicorn's default trust (`127.0.0.1`) makes every proxied
request look like the proxy — every browser sharing one bucket. `limits`
is also a transitive dependency of a library that is removable (the
observability stack), a coupling DD-238's removal notes must keep straight.

**Alternatives.** (a) The pure-ASGI middleware (built first) — removed for
the reasons above; kept as a fallback only if a deployment runs the server
without the webapp edge and wants a limiter (the server has no knob for it
now). (b) slowapi — refused: Flask/FastAPI decorator middleware, same
per-process limitation, new vocabulary (strategy/storage) for one rule.
(c) `X-Forwarded-For`-keyed limiting in nginx (`realip` module) — refused:
the browser cannot spoof the TCP address nginx sees; the webapp is the only
front door, no realip hop is needed. (d) Elasticsearch-side throttling
(`search.max_concurrent_shard_requests`) — refused for this increment: it
protects the store from the server, not the server from browsers.

**Consequences.** The refusal is nginx's 429 (HTML, no Atlas error body, no
`Retry-After` — `limit_req` sends none): DV-87 records the deviation, the
webapp's alert drawer (ALR-05) is the UX for the refused call. Deployments
that front the server with something other than the webapp nginx get no
limiter — that is the product boundary, stated in the spec. A deployment
whose internal callers arrive from public addresses must extend the geo
allowlist. `forwarded_allow_ips` ships `127.0.0.1` (uvicorn's own default —
the setting exists to _name the proxy_, not to trust more by default). Next
free DD: 239.

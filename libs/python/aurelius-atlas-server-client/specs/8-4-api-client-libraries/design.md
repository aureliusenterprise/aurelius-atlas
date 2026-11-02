# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-203. The wire contract lives in a client library; the app imports it

- **Status:** Accepted
- **Increment:** 8.4
- **Date:** 2026-10-23

**Decision.** Each Python HTTP API gets an accompanying library under
`libs/python/` that owns its wire contract — the pydantic request/response models —
and an API client for it: `aurelius-atlas-server-client`,
`aurelius-atlas-data2model-client`, `aurelius-atlas-lineage-model-client`,
`aurelius-atlas-validate-entity-client`. The models **move** out of the app that
served them (`ExtractionRequest` and the rule family out of `data2model.rules`;
`LineageInfo`/`EntityHeaderLite`/`LineageRelation`/`Direction` out of
`lineage_model.lineage`) and the response models the apps never had
(`ExtractionResponse`, `ValidationResponse`, the admin shapes) are written there.
The app then imports its own contract from the library (CL-07), and a consumer and
the server validate against one class. The app keeps its logic — `data2model` keeps
`types.py`/`extract.py`, `lineage-model` keeps `flatten_relations`/`LINEAGE_RULES`/
`UpstreamError` — only the _contract_ relocates.

**Reason.** Before 8.4 the contract was scattered and half-absent: the server answers
`.to_json()` dicts with no response models, `data2model` answers an untyped
`dict[str, Any]`, `validate-entity` answers a `dict` constant, and there is no Python
client at all (`aurelius-atlas-sdk` is utility code; the only outbound calls are
ad-hoc `httpx`). One home per contract removes the drift the Angular data-access lib
already fights (its DTOs are hand-mirrored from `aurelius_atlas_model`), and gives
every API a typed caller for free — `lineage-model` calls `data2model` and Atlas
through clients, so the 8.2 chain's payload validates as the 8.1 server's body
(CL-21). It is the pattern the workspace already runs for the server's _domain_
models (`aurelius-atlas-model`, DD-002/DD-020: models with no I/O, imported by every
layer); 8.4 extends it to the _REST_ contract and the client.

**Alternatives.** (a) Keep models in-app, have the library mirror them (refused —
two copies drift, the exact failure the Angular side lives with). (b) One
consolidated `aurelius-atlas-client` for all four APIs (refused — the removable-slice
and per-project `AGENTS.md` convention wants a consumer to depend on only the API it
calls; a shared lib would tie the aux APIs and the server together). (c) Generate the
clients from the OpenAPI schema (deferred — hand-written contracts are reviewable and
parity-guarded (ADR 052); a generator is a tooling increment of its own).

**Consequences.** The four libraries join the uv workspace and, being Atlas projects
under ADR 049, every public function needs a `covers`-named test (CL ids, this
increment's spec). `data2model.rules` becomes a thin re-export of the client lib's
family, so the app's DTM docstrings and the 8.1 tests keep citing the same names. The
Angular data-access lib stays hand-mirrored (a Python→TypeScript contract generator is
out of scope). The client home is per-API, so increment 5.1 adds `AtlasClient.get_lineage`
and 2.x–6.x add the entity/search routes to the _server_ client as they ship.

### DD-204. Clients are async httpx with an injectable transport, and read no env

- **Status:** Accepted (the construction sentence — base URL plus TLS/timeout/transport
  overrides — is superseded by DD-205: the `httpx.AsyncClient` is provided externally)
- **Increment:** 8.4
- **Date:** 2026-10-23

**Decision.** Each client wraps an `httpx.AsyncClient` (not a sync `Client`), built
from a base URL, a **token source** (a callable yielding the bearer token), and
optional `verify`/`timeout`/`transport` overrides. The transport is injectable so a
test answers it with a `MockTransport` and no socket opens — the DD-200 seam, made
async. A non-2xx answer raises the library's `*ClientError` (status + parsed
`{errorCode, errorMessage}`); an unreachable upstream propagates as `httpx`'s own
`RequestError` — mapping a transport failure to an HTTP status stays the **app's**
job (5.1's/LM-07's DV-80), not the client's (CL-04/CL-05). A client library reads no
environment variables; apps pass their settings' values (the libs-python rule, as
`aurelius-atlas-auth` and `aurelius-atlas-otel`).

**Reason.** Async is the workspace's outbound direction: the parity harness injects
an `httpx.AsyncClient`, FastAPI routes are `async def`, and the 8.2 chain (fetch
lineage, then extract) is two awaits that a sync client serialises. The
`httpx.Client` the app used (8.2's `_http`) was the odd sync holdout. The token
_source_ is a callable, not a stored token, so 8.2's browser-token forwarding
(LM-04 — forward the caller's raw token to both upstreams) is one source, not a
special case, and the same client serves a long-lived service identity. Keeping
transport-failure→status mapping in the app is DD-200/LM-07's existing split (the
client raises, the route answers 502): a shared client that invents a status would
steal that decision from the specs that own it.

**Alternatives.** (a) Sync `httpx.Client` (refused — the parity harness and async
routes are async; a sync client forces `run_in_threadpool` in every caller).
(b) Both a sync and an async client per API (refused — doubles the public surface
ADR 049 must name, for no in-workspace caller that is sync). (c) The client maps
`RequestError` to a 502 (refused — DV-80's mapping is LM-07's rule, app-scope; a
library that answers HTTP codes it never received would drift from the spec).

**Consequences.** `lineage-model`'s routes become `async def` and its
`create_app(settings, auth=None, atlas=None, d2m=None)` injects the two clients
(the `http=` seam becomes typed clients, DD-200). The 8.2 unit suite's
`FakeUpstream.client()` returns an `AsyncClient`. The clients are usable by the
dashboards' e2e and future 5.1 wiring unchanged. (The sentence moving
`UPSTREAM_TIMEOUT_SECONDS` into the client default is superseded by DD-205 —
the timeout lives on the externally built httpx client, which the app sets
from settings.)

### DD-205. The client's `httpx.AsyncClient` is provided externally

- **Status:** Accepted
- **Increment:** 8.4
- **Date:** 2026-10-23

**Decision.** Each client is constructed from an externally built
`httpx.AsyncClient` and a token source — `Client(http, token)` — replacing
DD-204's base-URL-plus-overrides construction (`Client(base_url, token, *,
verify, timeout, transport, http)`). The app builds the httpx client from its
own settings (TLS material, timeout) and passes it in. The client only borrows
the pool: it exposes **no close of its own** — no `aclose`, no context manager —
closing belongs to whoever built the httpx client, and `with_token` shares the
pool (`type(self)(self._http, token)`, no base-URL round-trip). The client's
request paths are **relative to the httpx client's base URL** (httpx appends
them), so the caller's URL works as given — pydantic's `HttpUrl` renders with a
trailing slash, and the app no longer trims it; the URL-shape expectation lives
in the client, where the route paths live. Tests pass an `AsyncClient` on the
recorder's `MockTransport` and no socket opens — CL-02's injection moves from
the transport to the whole client. The rest of DD-204 stands: async, token
source, no env, `*ClientError` on non-2xx, `httpx` errors propagating.

**Reason.** The six-parameter constructor duplicated what `httpx.AsyncClient`
already configures — `base_url`, `verify`, `timeout`, `transport` are its
constructor's arguments, copied through — and the copy forced an ownership
flag (`_owns_http`), a "close only what you built" rule, and a base-URL
round-trip in `with_token`. One dependency, injected, is the workspace's own
convention everywhere else (`aurelius-atlas-auth` and `aurelius-atlas-otel`
take an injectable `http`), and it makes the seam strictly wider: a caller can
pass a client with custom event hooks, proxies, limits, or auth, none of which
the pass-through constructor could express. The client library stays I/O-light:
it owns the paths, the bearer, the error mapping, and the models — the
transport stack is httpx's, configured by the app that owns its TLS and
settings.

**Alternatives.** (a) Keep the pass-through constructor (refused — six
parameters, an ownership flag, and a base-URL round-trip to express one
dependency; every setting it copies has an httpx-native way to be set). (b) An
optional `http` with a self-built default (refused — keeps both lifecycle
stories alive, the exact complexity being removed; an app that has settings
can build an `AsyncClient` in one line). (c) Keep `base_url` positional for
ergonomics (refused — the httpx client already carries the base URL; a second
copy can disagree with the first). (d) The client delegates `aclose`/context-
manager to the wrapped pool (refused — a borrower closing a pool it did not
build is the double-close bug in waiting; with one owner there is one close,
and the client keeps zero lifecycle surface). (e) The client rewrites the
pool's `base_url` (refused — mutating an injected dependency; the same effect
without side effects is relative request paths, httpx's own join semantics).

**Consequences.** The four clients take `(http, token)` and expose no close;
the `with_token` tests simplify with them (the closed-pool flag fixture is
just `http.aclose()`, the builder's). The `lineage-model` app builds the two
`httpx.AsyncClient`s in `create_app` when it builds the clients (CA file,
timeout — `UPSTREAM_TIMEOUT_SECONDS` stays the app's constant, DD-200; the
settings' URL passes through untrimmed), keeps them, and closes exactly those
pools in the app lifespan — an injected client's pool stays its builder's.
The app tests' fixtures build the httpx clients on the fake upstream's
transport — one transport per upstream, as before. Spec rules CL-01/CL-02 are
reworded in place (this increment is unmerged; the rule ids predate any
release).

**Addendum — the empty token (found by the server e2e).** The e2e suite drives
the containers through the clients, and the server's admin routes — open until
6.1 — are the first calls made with an empty token source (the app builds
`AtlasClient(http, "")`, and the e2e fixture has no user token to forward).
`f"Bearer {value}"` then sends the header value "Bearer " — with a trailing
space — which h11 rejects as an
illegal header value: over the recorders of the unit suites the bug was
invisible, since `MockTransport` does not validate headers. `_bearer` now sends
no authorization header at all for an empty token — the unauthenticated call,
which is what an empty source means (CL-03 reworded in place, unmerged);
auth-gated routes answer it 401/403 as any anonymous call, and 8.2's forwarding
is unchanged — a forwarded browser token is never empty.

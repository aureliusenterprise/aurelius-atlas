# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-206. The lineage-model's upstream breakers live in the app, on pybreaker's `calling()` seam

- **Status:** Accepted
- **Increment:** 8.5
- **Date:** 2026-10-23

**Decision.** The 8.2 app guards each upstream with its own `pybreaker`
`CircuitBreaker` (the workspace's existing breaker — `aurelius-atlas-auth`
guards the JWKS fetch with one, AUX-02): one for the Atlas `v2/lineage` feed,
one for the data2model `/extract`, built in `create_app` from
`breaker_fail_max`/`breaker_reset_timeout` (LM-15) and grouped with their
clients in the app-private `_Chain`. Each guarded call uses pybreaker's
documented **context-manager form** — `with breaker.calling(): await
client…` — and maps the open circuit's `CircuitBreakerError` to the 502 of
LM-12 at the call site. The `exclude` predicate is the documented callable
form: an upstream 4xx (the `*ClientError.status_code` of CL-04) is a fact, not
an outage (LM-13); a 5xx and a transport failure (CL-05) count.

**Reason.** A dead upstream turns every request into a full timeout on the
app's pool (DD-200's `UPSTREAM_TIMEOUT_SECONDS`), for every caller, forever;
LM-07's honest 502 does not protect the pool. The breaker belongs to the app
for the same reason the OTLP pipeline does (DD-197): it is the caller's
resilience policy, and the client libraries stay transport-only by DD-205 —
putting a breaker in `AtlasClient` would force a policy on every caller, and
a caller that _wants_ the timeout (the e2e suites, the 8.2 e2e chain's first
call) could not get it. One breaker per upstream, not one for the chain: the
204 of LM-05 must keep flowing past a dead data2model, and the extract must
keep serving the guids the feed can answer (LM-11).

**The seam.** pybreaker's async support is tornado-only (`call_async` is
built on `tornado.gen` and raises `NameError` on this Python — verified), and
the decorator form (`@breaker`) cannot express a per-request token-bound call.
The context manager is the documented third form: `calling()` drives the
generator through `call()`, so the generator opens the call (raising before it
when the circuit is open), the body awaits inside, and its outcome counts.
That nesting is the whole guard — one `with`, one `except CircuitBreakerError`
per call. The earlier form of this decision wrapped it in a `_guarded(breaker,
thunk, message)` helper with `functools.partial` thunks; that is more
indirection than the library needs, and `calling()` at the call site reads as
the docs read (LM-11). The breaker state is pybreaker's own — the app never
inspects it — so the half-open transition tests drive `half_open()` (the
documented management API) rather than sleeping through the reset timeout.

**Alternatives.** (a) A breaker in each client library (refused — DD-205's
libs are transports with models; a policy there is a policy for everyone, and
the LM/CL rules of 8.4 state what a client owns: paths, bearer, errors,
models). (b) One breaker for the chain (refused — couples the two upstreams'
fates; LM-11 counts them apart). (c) Count every 4xx as an outage (refused —
LM-05's 404 is the guid's, not the upstream's health; the auth library
excludes the issuer's 4xx for the same reason, AUX-02). (d) `aiocache`-style
caching of the 204 (refused — 8.2's scope note: no cache). (e) The
`_guarded(thunk)` helper (superseded by this entry's first revision — the
context manager at the call site is the documented, shallower form).

**Consequences.** `app.state.chain` carries the two clients and their two
breakers (the old per-upstream `app.state.atlas`/`.d2m` stay reachable through
it); the route function keeps its shape and calls the chain, which is one
guarded call per upstream. The chain's logic moves out of `create_app` into
the module-level `_run_chain` (the route was pushing the factory past ruff's
C901/PLR0915 — the same extraction DD-205's `_build_upstreams` made). The
e2e chain never opens a circuit (healthy upstreams), so the open path is
proven at unit level; the listener logs each state change (the AUX-02
pattern), and a breaker metric leg rides with the otel increments, not here.

### DD-207. The lineage-model app follows the example app's provider/route layout

**Date.** 2026-10-23
**Status.** Accepted (the `chain.py`/`LineageChain` section superseded by DD-208)
**Context.** After 8.5 the app was one 380-line `app.py`: the composition
root, the chain (`_Chain`), the breaker factories, the httpx/auth/telemetry
factories, the route, and the three error handlers in one module, with
private helpers (`_build_upstreams`, `_run_chain`, `_atlas_error`) reaching
across concerns. Every read of a request path jumped four layers down the
file. The FastAPI example app (`aurelius-atlas-fastapi-example`) shows the
workspace's structure for this shape: `globals.py` (name, logger,
constants), `providers/` (one factory per collaborator, settings in and
object out), `routes/` (APIRouter modules), and a thin `create_app` that
composes them. ADR 049's rule that every public function is named by a test
is what proves the split honest: each factory's tests run at its own seam.
**Decision.** The app is split along those lines, with two additions the
example has no need for:

- `globals.py` — `NAME`, `LOGGER`, the status codes, the fast-fail messages,
  the Atlas error code.
- `errors.py` — `UpstreamError` and `atlas_error` (the body the handlers
  share); `lineage.py` re-exports the class so its import path stays.
- `chain.py` — `LineageChain`, the public use case (`run`): fetch, flatten,
  extract, each guarded call translating the open circuit (LM-12) and the
  client errors (LM-05/LM-07) into `UpstreamError`; the empty graph answers
  `None` (the route's 204). This is DD-206's `_Chain` + `_run_chain`,
  merged and given its own module: the chain is the app's one concern, and
  the pair only existed to dodge `create_app`'s complexity limits.
- `providers/` — `auth.py` (the verifier, the library's `http` seam open),
  `upstreams.py` (`upstream_http`, `atlas_breaker`/`d2m_breaker`,
  `is_upstream_fact`, `build_chain` returning the chain and the pools the
  app owns — DD-205), `telemetry.py` (`ingest_pipeline`,
  `configure_telemetry`).
- `routes/` — `lineage.py` (`build_router(auth)`: the gated `GET /`, the
  chain read from `app.state`), `health.py` (the anonymous liveness).
- `app.py` — the composition root and nothing else: build, mount, wire the
  exception handlers (the mapping is the app's own contract, LM-05/LM-07/
  LM-12, so it stays at the root), telemetry.

The injectable seams are unchanged (`create_app(settings, auth, atlas,
d2m)`, DD-200), so the e2e chain and every 8.2/8.5 test ride on.
**Reason.** Separation of concerns the file had lost: a reader of
`chain.py` sees the use case, a reader of `providers/upstreams.py` sees the
resilience policy, `app.py` says only which collaborators exist. Dependency
injection, not service-locator: the factories take the settings and return
objects, `create_app` wires them — no module reads the environment, and the
tests replace collaborators by argument, not by monkeypatch (the pool
factory is patched only by the two DD-205 pool-ownership tests).
**Alternatives.** (a) Keep the single module — rejected: the nesting the
user asked twice to remove is the layout itself, and C901 was already
shaped by it (DD-205, DD-206's extractions). (b) FastAPI `Depends` factories
like the example's `providers/settings.py` — rejected for this app: its
collaborators are per-app singletons on `app.state` built once at
composition, not per-request dependencies, and `Depends` factories read the
environment (`get_settings`), which DD-200's injectable-settings seam
forbids. (c) The chain as a provider — rejected: it is the app's use case,
not one of its collaborators; `build_chain` composes it from the two
providers.
**Consequences.** `LineageChain` is public (ADR 049: named by
`test__aurelius_atlas_lineage_model_chain.py`), and each provider is named
by a test of its own; the trace inventory of the package grows, its gaps do
not. The route is a thin adapter: chain answer → verbatim
JSON, `None` → 204. `app.state` keeps the same shape (`chain`,
`atlas_breaker`, `d2m_breaker`), so 8.5's breaker tests are unchanged. The example app stays
the structural reference for the 8.x apps, not a wire contract (ADR 055).

### DD-208. The lineage flow lives in the route; the chain class is dissolved

**Date.** 2026-10-23
**Status.** accepted
**Context.** DD-207 gave the app's use case its own module and class:
`chain.py`'s `LineageChain.run` did fetch → flatten → extract, and the route
called it and mapped nothing. Review found that an extra layer: the example
app — the layout DD-207 adopted — has no use-case class. Its routes _are_ the
use cases, composed from provider functions (`find_all` opens a session and
builds the query; the SSE route drives the broadcaster). A class with one
method, called from exactly one route, hides the flow's shape (the 204 path,
the token forwarding, where each guard sits) behind a method name —
indirection, not separation.
**Decision.** Dissolve the class, keep DD-207's layout:

- `chain.py` and `LineageChain` are deleted. `routes/lineage.py` composes the
  flow directly — fetch, flatten, extract, answer verbatim — with the two
  guarded calls as private module helpers (`_fetch`, `_extract`): each wraps
  one client call in pybreaker's `calling()` seam (LM-11, DD-206 — the call
  site is the route, so the seam sits at the route) and translates the open
  circuit (LM-12), the lineage 404/400 and the extract failure into the
  `UpstreamError` of the status to answer. The empty graph answers 204 in
  place (LM-05/LM-06).
- `providers/upstreams.py` builds data, not behaviour: `build_upstreams`
  returns the two clients and the pools the app owns (DD-205);
  `atlas_breaker`/`d2m_breaker` stay factories.
- `create_app` puts `atlas`, `d2m`, `atlas_breaker`, `d2m_breaker` on
  `app.state` — the breaker names 8.5's rules and tests use are unchanged;
  LM-11's "exposed on `app.state`" stands.

The injectable seam, the handlers, and the wire behaviour are untouched.
**Reason.** The route is where the app's one request path is readable in one
function, in the order LM-01 states it; the providers stay the factories that
own _how_ a collaborator is built. DD-207's chain class solved the file-size
problem of the old `app.py`, which the provider/route split had already
solved — after DD-207 it solved nothing.
**Alternatives.** (a) Keep `LineageChain` — rejected: one-method class, one
caller; the user's read of the layout is the review. (b) Move `_fetch`/
`_extract` into `providers/upstreams.py` — rejected: guarding a call is the
flow's concern; the providers build collaborators, they do not serve
requests. (c) `LineageChain` as a plain dataclass (four fields, no methods) —
rejected: it would ride on `app.state` as one extra hop to four names.
**Consequences.** DD-207's layout stands; its `chain.py` section is
superseded by this entry. `app.state` gains `atlas`/`d2m` and loses `chain`.
The chain-module test file is deleted — every fact it proved (verbatim
answer, forwarding, 204s, failure mapping, open-circuit fast-fail) is
proven at the app seam by `test__app.py`/`test__lineage.py` (LM-01..LM-07,
LM-12), and the factories by `test__…_providers_upstreams.py`. The e2e chain
is unchanged.

### DD-210. Telemetry goes native: the OTel SDK replaces the logfire shell

- **Status:** Proposed
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row — no Atlas REST semantics)
- **Date:** 2026-10-23

**Decision.** All five Python apps (the Atlas server, the FastAPI example,
data2model, lineage-model, validate-entity) drop `logfire` and configure
OpenTelemetry natively. The `aurelius-atlas-otel` lib gains `telemetry.py`:
`build_providers` assembles the SDK `TracerProvider`/`MeterProvider`/
`LoggerProvider` from a service name/version, the app-built ingest pipeline
(DD-196's `build_otlp_pipeline` pair, now a single `pipeline=` parameter), a
standard-OTLP **env leg** that switches on when `OTEL_EXPORTER_OTLP_ENDPOINT`
is present in the process environment, and a stdout **console leg** for
debug-level runs; `setup_telemetry` installs them on the OTel globals (the
set-once first call wins, as the FastAPI test harnesses create one app per
test), and `bridge_logging` attaches the supported
`opentelemetry-instrumentation-logging` handler to named loggers. The apps
call `setup_telemetry` plus the native instrumentors
(`FastAPIInstrumentor`, and the example's `HTTPXClientInstrumentor`/
`PsycopgInstrumentor`); the example's SSE gauge registers through
`metrics.get_meter().create_observable_gauge`, and its settings' level type
becomes a plain `Literal` (the set logfire's `LevelName` carried). The wire
to the collector is plain OTLP/HTTP on both legs, unchanged: the per-service
leg (4319, JWT per export, CIA-07) and the example's legacy leg (4321, the
shared static bearer — exactly the static-header shape the SDK reads from
`OTEL_EXPORTER_OTLP_HEADERS`, CIA-10). This supersedes DD-196's logfire
integration detail (`additional_span_processors` /
`MetricsOptions.additional_readers` — the mechanism is the same app-built
pair, now installed by the lib instead of adopted by the shell) and DD-209's
copy of the `logfire.configure` block.

**Reason.** Every logfire use was a thin wrapper: `send_to_logfire=False`
in all five apps (the SaaS is never contacted), no structured logging
(`logfire.info`) and no `@logfire.instrument` decorators anywhere, and
`instrument_fastapi`/`httpx`/`psycopg` are the native
`opentelemetry-instrumentation-*` packages behind a rename. The one feature
of value — the dev console — is replaced by `ConsoleSpanExporter`/
`ConsoleLogRecordExporter` on debug runs, where the extra verbosity is free.
The wrapper also caused the workspace's import oddity: the apps imported
`opentelemetry.*` symbols (the example's `Observation`, `LoggingHandler`)
through a dependency declared on logfire, and the otel lib carried lazy
"arrives transitively via logfire" imports while already declaring
`opentelemetry-sdk` directly. Native providers make the dependency graph
honest: each app declares what it imports.

**Alternatives.** Keep logfire (refused — a wrapper with one vendored
feature, paid in a transitive dependency graph and a second config surface;
the collector stack is the observability product, logfire's console was its
only local value). Console export at info level (refused — the SDK's span
JSON dwarfs the request logs; the dev console earns its keep at debug, and
debug already implies verbose). `LoggingInstrumentor().instrument()` for the
log bridge (refused — it attaches on the _root_ logger and installs a record
factory; the example's contract is per-named-logger handlers with
propagation off, which `bridge_logging` keeps). Keeping logfire on the
example app alone for its log tail (refused — one shell, one mechanism, and
the native log pipeline covers the tail: `logs=True` builds the logger
provider the bridge feeds).

**Consequences.** Five pyprojects swap `logfire[...]` for the native
`opentelemetry-instrumentation-*` packages (locked at the same
`0.65b0`/`1.44.0` the shell pinned); `uv.lock` loses logfire. The otel lib
gains `opentelemetry-instrumentation-logging` (the supported handler — the
SDK's own `LoggingHandler` is deprecated in 1.44). The example's legacy leg
is now the SDK reading standard env: its `.env`/compose pair
(`OTEL_EXPORTER_OTLP_ENDPOINT`/`_CERTIFICATE`/`_HEADERS`) is unchanged —
DD-196's CIA-10 posture, restated without the shell. The otel lib reads the
standard `OTEL_EXPORTER_OTLP_ENDPOINT` env var — the one exception to its
"reads no env vars" rule, recorded in its `AGENTS.md` (a third-party-runtime
name, bare by the workspace's env-prefix rule). Unit specs: the lib gains
`test__telemetry.py` (the legs, the install guard, the bridge — CIA-07/
CIA-10); the three 8.x apps' telemetry specs swap the
`logfire.configure`-monkeypatch seam for `setup_telemetry`/
`FastAPIInstrumentor` on the app module. `setup_telemetry` is set-once per
process, so a second `create_app` in one test process keeps the first
call's providers — the same lifecycle logfire's `configure` had. The e2e
suites are untouched — they ride the wire (the collector accepts the same
OTLP/HTTP pushes on the same legs). AUX-03's rule id stands (unset credential
= no OTLP leg); its "console only" wording now means the stdout leg of
debug-level runs — at info/warning an app with no credential exports
nothing, where logfire's pretty console used to print (this supersedes that
detail of the 8.0 spec's AUX-03 row).

**Chain stitching (same increment).** The switch kept the example's httpx
instrumentation 1:1 (`logfire.instrument_httpx` → `HTTPXClientInstrumentor`),
and the e2e walk showed what the other apps deliberately left uninstrumented:
the 8.2 chain's upstream calls (lineage-model → Atlas fetch, → data2model
extract, LM-04) carried no W3C `traceparent`, so every service rooted its own
trace in Tempo. lineage-model graduates: `HTTPXClientInstrumentor` rides its
composition root, so the caller's trace rides the chain's httpx calls and the
8.2 chain (browser → lineage-model → data2model) is one trace. The e2e suite
adds the stitch probe (`test__the_chain_shares_one_trace_with_the_caller`):
a minted trace id as `traceparent`, then the Tempo read-back shows the
lineage-model `GET /` span and the data2model `POST /extract` span under the
caller's id (LM-04's calls, DD-210). The issuer mints (the auth lib) and the
OTLP ingest shim stay uninstrumented — mint spans are per-request noise, and
instrumenting the exporter is a self-referential span loop.

**Every HTTP call visible (same increment).** The issuer-mint refusal above
is reversed for httpx (user call): every FastAPI app that reaches the network
over httpx now installs `HTTPXClientInstrumentor` — the example (as before),
lineage-model (the chain, above), and data2model/validate-entity (the auth
library's issuer verification and JWKS fetches ride the caller's trace). The
server's outbound legs are deliberately not httpx: its store calls ride the
elasticsearch client (below, natively instrumented) and its OTLP export rides
`requests` inside the ingest shim, which stays uninstrumented (the
self-referential span loop above stands).
`build_providers` registers the per-process system metrics on every app's
meter provider (DD-210): the system-metrics package's default instrument set
minus the host-wide `system.*` group — the dev/e2e apps share one host, so
five containers would report the same host series five times (infra host
metrics ride the pullers). The set lands in Prometheus next to the RED series
(`process_cpu_time_seconds_total`, `process_memory_usage_bytes`,
`cpython_gc_collections_total`, per `exported_job`). Elasticsearch needs no
package at all: elasticsearch-py
≥ 8.13 emits a span per store operation on the global tracer, on by default
(the contrib package is stale and self-disables on native clients), so the
server's ES spans ride the app-owned leg as installed (`db.system.name`,
`db.operation.name` on each). The server suite adds the guard probe
(`test__the_store_calls_ride_the_server_trace`): a minted `traceparent` on a
typedefs call, and the Tempo read-back requires the request span and an
elasticsearch span under the caller's trace id.

### DD-211. httpx2 replaces httpx across the HTTP surface

- **Status:** Proposed
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row — no
  Atlas REST semantics)
- **Date:** 2026-10-24

**Decision.** Every first-party httpx use moves to **httpx2** (`pydantic/httpx2`,
the Pydantic-stewardship continuation of httpx): the nine pyprojects that
required `httpx>=0.28.1` (the example, lineage-model, the auth lib, the five
client libs, parity, sdk) require `httpx2>=2.0.0` instead, the six
FastAPI-dependent pyprojects raise their floor to `fastapi>=0.162.0` (the first
release whose extras require httpx2), and every `import httpx` becomes
`import httpx2 as httpx` — the alias starlette's own testclient uses, keeping
call sites (`httpx.AsyncClient`, `httpx.RequestError`, …) untouched. The four
apps' `configure_telemetry` swap `HTTPXClientInstrumentor` for the
`HTTPX2ClientInstrumentor` that `opentelemetry-instrumentation-httpx` 0.65b0
already ships (same import path, same spans: `http.method`/`http.url`/
`http.status_code`). Where a CA file configured TLS, the deprecated
`verify=<path>` string becomes `verify=ssl.create_default_context(cafile=...)`
(the auth lib, the example's outbound provider, lineage-model's upstreams).

**Reason.** Starlette 1.6 deprecates `httpx` with its `TestClient`
(`StarletteDeprecationWarning: … install httpx2 instead` — the warning the user
reported), and httpx2 is where httpx's stewardship continues. The migration
surface is small and verified: every symbol the repo uses exists on httpx2
(`Client`, `AsyncClient`, `Response`, `MockTransport`, `ASGITransport`,
`Timeout`, the error family, `codes`, `QueryParams`); OTel instruments httpx2
natively at 0.65b0, so DD-210's "every HTTP call visible" rule rides unchanged;
fastapi core never required httpx at all (only its extras), so bumping to
0.162.0 drops the httpx pin from the apps' transitive closure with no code
change — `fastapi.testclient` is unchanged and silently rides httpx2.

**Deliberate deviations.** httpx2 reads the **OS trust store** by default
(`truststore`), not certifi: a deployment that trusted a CA through
`SSL_CERT_FILE` for httpx must pass `verify=ssl.create_default_context(cafile=…)`
(the pattern this DD lands on the three CA-aware sites). `verify=<str>` is
deprecated on httpx2, which is why the string CA paths are gone from first-party
code. **httpx stays in the venv**, pulled by `python-keycloak` (dev-only, the
example's e2e fixtures): its sync path rides `requests` — which takes a str CA
path and rejects an `SSLContext` — and its async path is classic httpx, whose
`verify=<path>` deprecation warning is python-keycloak's own, not first-party.
Starlette prefers httpx2 when both are importable, so the TestClient warning is
gone with both installed.

**Consequences.** `uv.lock`: `httpx2`/`httpcore2`/`truststore`/`httpx2-jsfetch`
in, `fastapi` 0.141.1 → 0.162.0, `httpx` demoted to a python-keycloak-only
dependency. The auth lib gains `_tls_context` (a CA-rooted context, or system
trust when unconfigured — the same trust httpx's `verify=<path>`/`verify=True`
built); the example's provider spec asserts the context, not the string. The
fix rides DD-210's audit trail: 51 e2e (all five apps, rebuilt images bundling
the httpx2 wheels) and the per-project unit suites pass, the
`StarletteDeprecationWarning` is gone from every warnings summary, and the
OTel spans over httpx2 are read back from Tempo by the unchanged chain and
store probes.

### DD-212. The 8.x apps' app/scenario test modules carry their package name

- **Status:** Accepted
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row —
  no Atlas REST semantics)
- **Date:** 2026-10-24

**Context.** A repository-wide pytest run (`uv run pytest apps libs`, the
root's Common Commands) fails collection with `import file mismatch`: the three
8.x apps each carry `tests/test__app.py` and `tests/test__scenarios.py`. The
`tests/` dirs are not packages (INP001 is waived for test files), so pytest's
default prepend import mode puts each `tests/` dir on `sys.path` and imports by
basename — the first app collected owns the module name and the other two
error. Per-app runs (`nx test`, `cwd` = project root) never collided; the
collision is what a uniform basename across apps means for root collection.

**Decision.** The six files take the package-prefixed names the apps' sibling
test files already use (`test__<package>_<module>.py`): `test__app.py` →
`test__aurelius_atlas_data2model_app.py`, `test__aurelius_atlas_lineage_model_app.py`,
`test__aurelius_atlas_validate_entity_app.py`, and the same for the three
`test__scenarios.py`. The specs' test lists cite the new names.

**Reason.** Unique basenames are pytest's own hint for this error, and the
prefix is each app's established convention for every other test module
(`test__aurelius_atlas_data2model_settings.py`, …) — the collision is the two
names that predate DD-209's layout settling. Renaming all three apps (not just
the two losers of the import race) keeps the family uniform.

**Alternatives.** (a) Add `__init__.py` to every `tests/` dir — rejected: the
conftest and tests/ helper imports (the 8.2 fake upstream, the 8.4 recorders)
and the pyright `extraPaths` execution environments are built on `tests/`
riding `sys.path`, not on it being a package. (b) `importmode=importlib` at the
root — rejected: it changes collection semantics workspace-wide to fix two
names. (c) Rename only data2model's pair (it wins the alphabetical race) —
rejected: the other two stay collision-prone for every future sibling app.

**Consequences.** Rule ids and `covers` markers are untouched — the trace
plugin reads them from the files, and the per-app `trace.json`/`junit.xml`/
`coverage.xml` artifacts (untracked, `tools/plugins/python.ts`) regenerate with
the new nodeids on the next `nx test -c ci`. DD-208's and DD-209's
Consequences mention `test__app.py` as history and are not edited. The specs'
test lists (8.1, 8.2, 8.3, 8.5) name the new files in the same change.

### DD-213. The lineage guid is a UUID on every typed surface

- **Status:** Accepted
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row —
  the guid's type is a contract detail of the 8.2/8.4 surfaces, DV-78)
- **Date:** 2026-10-24

**Context.** The lineage chain carried the entity guid as `str` end to end:
`LineageModelParams.guid`, `AtlasClient.get_lineage`, `LineageModelClient.get`,
the app route's query parameter, `EntityHeaderLite.guid`, `LineageRelation`'s
endpoint ids, and `LineageInfo.guid_entity_map`'s keys. Atlas's own guids are
UUIDs (`Entity.getGuidAsString` returns the canonical string of a `UUID`), and
the 5.1 feed will answer `v2/lineage/{guid}` with them. A `str` guid accepts any
token — the fixtures grew readable ids (`e-in`) that no Atlas entity could have,
and a malformed guid travels all the way to the upstream before failing.

**Decision.** Every lineage guid is `uuid.UUID` on the typed surface: the
client models and methods, the app route's `guid` query parameter (FastAPI
parses it, so a non-UUID is DV-73's `400` before any upstream call),
`EntityHeaderLite.guid`, `LineageRelation.fromEntityId`/`toEntityId`, and
`LineageInfo.guidEntityMap`'s keys. `LineageRelation.relationshipId` stays
`str` — it is a relation id, not an entity guid, and the legacy fixtures give
it readable values. The Java-parity typedef/instance guids of the server
surface (`aurelius-atlas-model`) are untouched — this is the lineage chain
only. Fixtures use fixed UUIDs (`00000000-0000-4000-8000-0000000000NN`);
names, labels, and relation ids stay readable.

**Reason.** Pydantic parses and serialises UUIDs natively (the OpenAPI schema
gains `format: uuid`; JSON string keys coerce into `dict[UUID, ...]`), httpx
stringifies a UUID into the canonical lowercase form on the wire, and the
extract engine's `_legacy_str` stringifies the UUID cells of the flattened
rows — so the wire stays byte-identical to Atlas's, while every Python
surface rejects a malformed guid at its own boundary. A `str`-typed chain
would leave the route answering DV-73's 400 only for _missing_ guids and
forwarding garbage for present-but-invalid ones.

**Alternatives.** (a) `Annotated[str, UuidCheck]` validators — rejected:
re-implements what `UUID` gives for free, and the schema loses `format:
uuid`. (b) Typing the Java-parity guids too — rejected for now: the 1.x/5.x
surfaces mirror Atlas's Java DTOs, where guid is `String` at the wire;
DV-78's row scopes this to the lineage chain, and a parity spec change is
Java-reference work (ADR 052), not a client-library detail.

**Consequences.** The e2e fixture file is named for its guid, so
`e2e/fixtures/v2/lineage/e-in` becomes the UUID-named file the fixture
`http.server` maps `/v2/lineage/<guid>` onto. `test__lineage.py` gains
`test__a_guid_that_is_not_a_uuid_is_400` (LM-07); the dangling-guid test's
endpoint becomes a well-formed UUID the map lacks — a malformed guid can no
longer reach the flattening at all, which is the point.

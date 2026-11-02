# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-239. The edge exports spans on the legacy leg, built in the dev-image stage

- **Status:** Accepted
- **Increment:** 9.4
- **Date:** 2026-10-28

**Decision.** The webapp's nginx becomes an OTLP producer through the native
`ngx_otel_module` (v0.1.2), compiled in a Docker builder stage on
`dhi.io/nginx:1.30-alpine3.24-dev` against the exact nginx source the runtime
image ships, loaded via the main-context include the hardened image already
provides (`/etc/nginx/modules/*.conf`), and exporting the `/api/` spans to the
collector's **legacy gRPC leg** (4320: TLS, CA-pinned, shared ingest token).
The edge span propagates W3C context (`extract|inject`), so it stitches
browser-app trace → edge span → server request span; static assets stay
untraced. The edge is a producer, not a user: the collector stamps no user
identity on it (CIA-09's rule, edge edition). ETR-01..03. (Numbering note:
PR #155 reserves DD-237/238; 239 here assumes it merges first.)

**Reason.** The edge is the browser's only entry point and the one hop the
stack cannot see; once 9.3's limiter lands, refusals (429) exist _only_ at the
edge — nginx's refusal lines go to container stderr, which the collector does
not collect (OTLP-only receivers), so without this the event is invisible in
Tempo/Loki/Grafana. The module's native span carries the edge's own view
(`http.status_code`, `net.sock.peer.addr`, the matched route) and joins the
trace the browser started. The 2022 blog's Lua/OpenTelemetry-Collector-sidecar
route is obsolete next to the native module (nginx measures third-party
tracing at ~50% request cost, native at 10-15%).

**Alternatives.** (a) Per-service OAuth like every other producer — the
module's export headers are config-parse-time **static strings** with no
refresh hook (source: `addExporterHeader` validates at parse, the exporter
builds once in `initWorkerProcess`), so a minted Keycloak JWT expires minutes
in; a gateway collector presenting `oauth2client` to the services leg is the
recorded upgrade path, not this increment. The legacy leg is the defined home
for producers that cannot present a JWT (CIA-10 — Keycloak and the FastAPI
example ride it). (b) The `-dev` image as runtime — it is a toolchain, not a
product; the runtime stage is the hardened image plus the module's 93-lib
closure (~42 MB, gRPC/protobuf/abseil/ICU: gRPC pulls ICU at runtime, verified
by ldd). (c) `filelog`-tailing nginx's stderr into Loki — answers "where are
the refusal logs" with lines, not spans: no trace join, no client-side
stitch, and the collector has no container-log receiver today; the span
supersedes the log line. (d) The module from nginx.org's prebuilt dynmodules —
built for glibc nginx.org binaries; our base is the hardened musl image
(module signature is feature-flag checked, and musl will not resolve Alpine's
dangling soname symlinks — the builder tars the closure dereferenced, `-h`).

**Consequences.** The webapp image grows 14→56 MB; the SBOM/license report
gains grpc/protobuf/abseil/re2/icu (Apache/BSD). The builder pins the v0.1.2
tag with the cmake-4 policy flag (its `cmake_minimum_required` predates 3.5)
and apk's `python-3.14` (the dev image's xcb-proto resolves 3.14; bare
`python` is 3.15 now) — reproducible-build facts recorded here.
`limit_req` and this module share the `/api/` location: the limiter refuses
before the span's `http.status_code` records the 429 (the module samples at
the rewrite phase, completes at the log phase — a refused request's span is
real, proven in the prototype burst). The v0.1.x line is 2023-frozen
(4 open issues, no maintainer activity); re-evaluate at the next nginx
baseline (the 1.30 signature check is the compatibility gate — a mismatched
module fails at config parse, loudly, at boot). Next free DD: 240.

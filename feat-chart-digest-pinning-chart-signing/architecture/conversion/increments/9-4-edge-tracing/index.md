# 9.4 Edge tracing: the webapp's nginx joins the trace

- **Status:** in progress
- **Pull request:** [\#156](<https://github.com/aureliusenterprise/aurelius-atlas/pull/156>)
- **Records:** DD-239

## Scope

The webapp's nginx is the browser's only entry point and, until now, the one hop invisible to the observability stack: a request refused at the edge (9.3's limiter) never reaches the server, so it leaves no span, no log in Loki, nothing in Tempo. This increment makes the edge a first-class tracing producer:

- **The image carries the native OTel module** (`ngx_otel_module`), built in a Docker builder stage on `dhi.io/nginx:1.30-alpine3.24-dev` — the hardened image plus apk and the distro's build tree — against the exact nginx the runtime image runs, and loaded through the main-context include the hardened image already ships (`ETR-01`, [DD-239](<https://aureliusenterprise.github.io/feat-chart-digest-pinning-chart-signing/architecture/conversion/design-log/#dd-239--the-edge-exports-spans-on-the-legacy-leg-built-in-the-dev-image-stage>)).
- **Every `/api/` request is a span**: exported to the collector over OTLP/gRPC (TLS, CA-pinned, shared ingest token — the legacy leg), W3C context propagated, so the span stitches the browser-app trace to the server's request span; static assets stay untraced (`ETR-01`).
- **The span is the edge's own view**: method/target/route/status, the client's socket address, and the response status the edge answered — `429` refusals included, once 9.3 lands (`ETR-02`).
- **The edge is attributed as a producer, not a user**: the exporter rides the legacy leg (shared token), so the collector stamps no user identity on it per the CIA-09 rule; per-user attribution stays the browser leg's job (`ETR-03`).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `429` refusals visible in Tempo (needs the limiter) | 9.3 (PR \#155) — the ride is this increment's span |
| Per-service OAuth for the edge (Keycloak client, minted JWTs) | the gateway-collector upgrade path (DD-239) |
| nginx container logs in Loki (docker driver / collector `filelog`) | not scheduled — spans carry the refusal signal |
| Edge metrics (stub\_status/VTS scraped by Prometheus) | not scheduled |

## Semantics

| Id | Rule |
| --- | --- |
| ETR-01 | The webapp image loads the native OTel module and exports a span for every request served under `/api/` to the collector's legacy gRPC leg (OTLP/gRPC, TLS with the deployment's CA as trust anchor, `Authorization: Bearer <ingest token>` static header); W3C trace context is `propagate` — an inbound `traceparent` becomes the span's parent, the span's id becomes the upstream server span's parent; the server block keeps `otel_trace off` so static assets produce no spans |
| ETR-02 | The edge span carries the edge's view of the request: `http.method`, `http.target`, `http.route` (the matched location), `http.status_code` (the status nginx answered, refusals included), and `net.sock.peer.addr` (the client the edge sees) — the module's default attribute set, span name = the matched location name |
| ETR-03 | Edge telemetry is producer-attributed, not user-attributed: the exporter authenticates with the shared ingest token (legacy leg, CIA-10 class), and the collector stamps no user identity on what it receives (the DD-194 empty-upsert rule — `enduser.id` arrives empty, and Tempo stores it absent) — user identity rides the browser leg's own OIDC pushes only |

## Java origin

None. Apache Atlas 2.4.0 ships no edge tracing — nginx, OTLP, and the collector are Aurelius-side infrastructure (9.1/9.2 set the precedent: observability rules carry no Java twin).

## Deviations

None. The increment changes no REST semantics.

## Acceptance

- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp_edge_tracing.py` — GET `/api/atlas/admin/version` with a minted `traceparent`: Tempo returns the trace containing the edge span (`service.name=aurelius-atlas-webapp-edge`, `GET`/`/api/atlas/admin/version`, status 200, peer addr), parented to the injected id, with the server's request span its child (ETR-01, ETR-02); the edge resource carries no `enduser.id` (ETR-03).
- The image boot is itself the module proof: nginx refuses to start with a broken `load_module`/`otel_exporter` config, and every webapp e2e run boots the image — the suite passing is the config-parse gate (no standalone smoke test).
- The e2e stack runs the real exporter path (TLS + CA + shared token → the dev collector's legacy leg on the observability network): the Tempo read-back above is the end-to-end proof, not a mocked sink.
- `nx e2e aurelius-atlas-webapp` (full suite) — the shipped image + e2e nginx config + compose topology, with the browser-app suites riding the untraced asset path unchanged.

# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-193. Collector ingest is authenticated in two legs: user JWTs for browsers, a shared token for services

- **Status:** Proposed
- **Increment:** 7.17
- **Date:** 2026-10-22

**Decision.** The OTel collector's OTLP receivers stop accepting anonymous
writes, with a per-leg proof of the writer (CIA-01). The **browser leg**
(HTTP 4318) authenticates the signed-in user: the collector's `oidc`
extension validates the Keycloak access token the SPA sends — issuer,
signature, and the `otel-collector` audience the realm's `otel-ingest` client
scope mints — so every span and metric carries the user's identity (the `sub`
claim). The **service leg** (gRPC 4317, HTTP 4319) keeps a shared ingest token
(`bearertokenauth`): headless producers — the Atlas server, the FastAPI
example, Keycloak's own OTLP, the slice pullers — present it through the
standard `OTEL_EXPORTER_OTLP_HEADERS` / their exporter's `headers` block
(CIA-04). The browser's proxies pass the `Authorization` header through
untouched (nginx's default, and http-proxy's): the proxy is a pipe, not a
credential (CIA-02). The SPA attaches the token through the OTLP exporters'
`headers` factory — an async callback OTel invokes per export (the OTLP
transport rides XHR/fetch outside Angular's HttpClient, so the bearer
interceptor cannot cover it). The seam is shared, not per-app:
`createAureliusOtelIngestAuth` in `aurelius-atlas-observability` carries the
factory and an `attach` binding, and each app hands it the live `Keycloak`
client in a `provideAppInitializer` (the webapp's sits inside its telemetry
gate — with telemetry off there is no exporter to feed); no registration
order is load-bearing, as the factory resolves the token at export time.
`updateToken(30)` per export covers the dev realm's 60s token. The collector's
host publishes pin to 127.0.0.1 (4317/4318/4319) and the prometheus
exporter's publish drops — CIA-03. The issuer URL is compose env (dev default
at the plaintext `:8080` issuer, ADR 039's relaxation; the e2e conftests
override with the TLS `:8443` issuer plus the shared dev CA, matching each
stack's `iss` claim); the extension discovers JWKS from the issuer itself and
needs Keycloak reachable at startup. The dev token lives in
`dev/observability/.env(.enc)` and every producer project's `.env.enc`.

**Reason.** ADR 039 states the collector's ingest rule as TLS — that proves
_which collector_ a writer reaches, not _who_ writes: on a dev machine the
published 4317/4318 accepted anonymous writes from anything that could route
to the Docker host, and through the webapp's own `/otel/` proxy from anywhere
that could reach the site. The credentials stack on the verified channel;
ADR 034's one collection point stays (a credential, not a hop). The browser
leg chooses user JWTs over a shared secret for **attribution**: forged
telemetry carries the forger's `sub` and is revocable per user, and the
telemetry's user joins the traces the SDK already correlates. This corrects
the claim made earlier in this increment's design (and in the NasTech
write-up's counterexample) that a public client makes a JWT gate worthless:
`publicClient` means the _client_ holds no secret, not that tokens are free —
auth-code + PKCE still requires the user's credentials, so "anyone with a
connection" becomes "anyone with an account", the same bar a shared proxy
secret sets, with identity for free.

**Alternatives.** One shared token on both legs, the proxy injecting the
browser's (this design's first cut, refused — it closes open ingest but
attributes nothing, and a leaked proxy secret forges un-attributed telemetry
forever; the user-JWT gate has the same bar and keeps the identity). Making
the `aurelius` client confidential (refused — an SPA is a public client by
definition: anything shipped in the bundle is public, keycloak-js's PKCE flow
rejects confidential clients, and confidentiality protects the client, not
the token — attribution rides the token's `sub`). Keycloak JWTs on the service
leg too (refused for now — Keycloak bootstrapping itself as its own
telemetry's issuer is a chicken/egg, the pullers need a client-credentials
`oauth2client` extension, the Python SDK's headers env is static so a 5-min
JWT needs a refresh shim, and the observability stack starts before Keycloak
by design — the per-service graduation stays open: the extension validates
JWKS for any audience. (Delivered by DD-196 in 7.18: the pullers'
`oauth2client` extension, the server's refresh shim, and the issuer-shaped
boot order each closed one named wall; Keycloak-native — the one producer
with no answer — keeps the shared token on the legacy leg.) `optional: true` on the OIDC receiver, or starting
OTel after auth, to keep pre-login telemetry flowing (both refused —
unauthenticated pass-through reopens the exact door this closes, and a
post-auth SDK start loses the cold-load Core Web Vitals the dashboard is
built on; the first-load telemetry loss is **accepted**, the login is the
telemetry gate). Keeping the seam per-app (refused at the review pass — the
first draft carried a byte-identical copy in each app config; the seam is
the OTLP transport's relation to auth, which is `aurelius-atlas-observability`'s
knowledge, and one tested copy beats two. The lib's exporter-agnostic rule
is untouched: the seam types its client structurally — `authenticated` /
`updateToken` / `token`, the same shape keycloak-angular's interceptor
reads — so the lib depends on a shape, not on `keycloak-js`).

**Consequences.** The browser leg makes Keycloak a dependency of browser
ingest: the collector fetches JWKS from it, the e2e conftests start Keycloak
before the collector's issuer is consulted, and a dev machine exporting
browser telemetry with Keycloak down sees 401s (the service leg keeps
flowing). Pre-login exports (the landing page's first spans/metrics) are
rejected — accepted. Every service producer must present the token, including
future ones — each slice's `nx serve`/e2e runs are the gate (CIA-04, the
webapp e2e's accepted-export test plus every slice's suite). The realm's
`otel-ingest` scope is part of the `aurelius` client contract: tokens minted
before a realm re-import carry no `aud` and are rejected (dev/keycloak
AGENTS.md). The e2e suites mint a real user token (password grant, the dev
sign-in user) to drive the browser-leg tests, and the collector's compose
gains `OTEL_COLLECTOR_OIDC_*` env with a `/dev-ca` CA mount;
`dev/observability` gains a `.env.enc`, so its compose targets now
`dependsOn` `decrypt` like every other slice. The NasTech pattern this
follows (OIDC extension on the HTTP receiver, user token from Keycloak) is
credited: <https://blog.nashtechglobal.com/secure-opentelemetry-collector-for-tracing-front-end/>

### DD-194. The collector stamps the verified user onto the telemetry: `enduser.id`

- **Status:** Accepted
- **Increment:** 7.17
- **Date:** 2026-10-22

**Decision.** DD-193's browser leg verifies the user's token; this makes the
verified identity ride the data (CIA-05). The collector's shared `resource`
processor copies the OIDC context's subject claim onto every browser-leg
push: `key: enduser.id, from_context: auth.claims.sub` (the claims land in
the request context under their **raw JWT names** — Keycloak's subject claim
is `sub`; the extension README's `auth.claims.subject` example fits issuers
that name the claim that, and a missing source upserts an **empty**
attribute, not nothing — verified against 0.162 with a Tempo read-back).
The attribute key is `enduser.id` (the semconv registry's key for a user
identifier; `subject` alone is ambiguous next to `service.name`). The
traces/metrics pipelines share the processor, so a user's spans and web
metrics carry it. On the metrics leg a `transform` processor
(`context: datapoint`, `set(attributes["enduser.id"],
resource.attributes["enduser.id"])`) promotes it to datapoint level, where
the prometheus exporter turns it into the `enduser_id` label — the exporter
keeps only a few resource attributes as labels (`service.name` →
`exported_job`) and drops the rest, so without the promotion the stamped
identity never reaches Prometheus. The service leg has no OIDC context: its
pushes carry `enduser.id=""` (empty upsert, above) — producers stay
unattributed, and the label is one constant value, no cardinality growth.

**Reason.** Attribution was the browser leg's reason for user JWTs over a
shared secret (DD-193): a forged push is attributable to the account that
minted the token. That clause is only true once the identity is ON the data
— verification alone leaves Tempo/Prometheus blind to which user a span came
from, and the dashboards (keyed on `service_name`/`exported_job`) cannot
answer "whose load is this". Tempo searches it as a resource attribute
(`{ .resource["enduser.id"] = "<sub>" }`, TraceQL 2.3 scoped syntax) and the
e2e reads it back through trace-by-id.

**Alternatives.** `resourcedetection` with an auth detector (refused — no
auth detector exists; the claim copy is the `resource`/`transform`
processors' job). Span-attribute copy instead of resource (refused — the
resource is the per-push envelope: one copy per push, every span in it
inherits; a span-level copy needs OTTL per span and misses metrics, whose
datapoints the transform already covers). `enduser.id` + `enduser.name`
(`preferred_username`) (deferred — the readable name doubles the PII surface
for a dev stack; the `sub` UUID is joinable to Keycloak's admin at query
time; add the display name with the audit slice if the dashboards need it).
Tempo's `metrics_generator` with `dimensions: [enduser.id]` (refused for
now — it would generate span-metrics/service-graphs series per user from
traces; the collector-side label promotion covers the dashboards, the
generator stays off as in the rest of the stack).

**Consequences.** `sub` (a UUID) is PII-adjacent: it is a persistent per-user
identifier inside telemetry retention — accepted for the dev stack, and the
production posture note is ADR 039's (the collector's own). Dashboards can
group by `enduser_id` (metrics) or filter `{ .resource["enduser.id"] = … }`
(Traces); Tempo's live-store search indexes span attributes only, so
resource-predicate searches hit backend blocks (older than ~30 min) —
Grafana's TraceQL UI handles the fan-out, the e2e asserts storage through
trace-by-id (`GET /api/traces/<id>?encoding=json` — Tempo 3.x's route is the
plural, the singular `api/trace/` 404s, and the default encoding is
protobuf). Pre-login telemetry stays lost (DD-193's accepted trade).

### DD-195. The collector rides out Keycloak's boot: bounded restart, awaited readiness

- **Status:** Accepted
- **Increment:** 7.17
- **Date:** 2026-10-22

**Decision.** DD-193's `oidc` extension discovers JWKS at extension start, so
the collector exits 1 whenever Keycloak is not answering yet. The boot order
makes that window structural: keycloak (and the postgres/elasticsearch slice
composes) attach `aurelius-atlas-dev-observability-network` as an **external**
network, so observability must come up first — Nx's `implicitDependencies`/
`^up` chain and the e2e conftest fixtures both start it before Keycloak. The
fix is therefore on the collector side, not the order: `restart: on-failure:15`
in `dev/observability/docker-compose.yaml` (Docker backs off 100ms doubling to
a 1min cap — ~15 attempts span ~6 minutes, far past Keycloak's boot, and the
bound means a Keycloak that never comes up ends in a loud `compose up --wait`
exit rather than an infinite crash loop). Keycloak's readiness gate is compose's
own: the conftest fixtures' `start()` runs `up --wait` and the keycloak service
carries a healthcheck, so the command returns when Keycloak is ready. The
fixtures' post-start `HealthcheckWaitStrategy` registration is dead code
(`waiting_for` is a setter, `start()` runs the strategies) and is removed from
the webapp/frontend-example conftests — it could never have worked: the strategy
reads docker-py `attrs`, which the `ComposeContainer` wrapper
`DockerCompose.get_container()` returns does not have (verified: it raises
`AttributeError` the moment it runs). The fastapi-example's dead registration
stays — its `_wait_for_dev_users` poll is that suite's real Keycloak gate.

**Reason.** Found as a full e2e failure: with a cold stack, `docker compose up
--wait` on observability exits 1 on the collector's first crash, every fixture
errors, and 90 tests never run. Verified: `up --wait`'s watcher survives the
intermediate exits and returns when the container lands on a running/exit-0
state, so the restart policy makes the cold start self-heal (collector ~30s
behind Keycloak's health).

**Alternatives.** Start Keycloak first (refused — the external-network
attachment makes the order structural, and the Nx graph would invert for a
dev-stack-only reason). A healthcheck-gated collector (refused — the image
is shell-less/hardened, and compose has no keycloak service to gate on from
this stack). A testcontainers `HealthcheckWaitStrategy` on the keycloak fixture
(refused — the strategy reads docker-py `attrs` the `ComposeContainer` wrapper
does not expose, so it raises `AttributeError`; `up --wait` already gates on the
service healthcheck). Retries inside the extension (refused — the oidc extension
has no retry knob; discovery hard-fails at start by design). An unbounded
`restart: on-failure` (refused — a permanently broken issuer then crash-loops
forever and `up --wait` never returns; the bounded count keeps the failure
loud).

**Consequences.** A cold `nx up`/e2e start costs the collector a few restart
cycles (~30s) — invisible behind Keycloak's own ~40s boot. The dev stack's
plaintext :8080 issuer keeps the same window. The nginx `/otel/` proxy in the
webapp/frontend-example e2e configs moves to a variable upstream
(`set $otel_upstream` + resolver) like the `/api/` block: a literal
`proxy_pass https://otel-collector:4318` resolves at config load, which fails
nginx while the collector is restarting (DD-195 makes that window normal). The
`set` must precede the `rewrite ... break` — `break` halts the rewrite module,
of which `set` is a directive, so a `set` after the rewrite never runs and the
upstream host resolves empty (500, "no host in upstream"; the shipped
production template orders them the same way, discovered by measurement). The
`collector_container` fixture polls for the settled running state — a restarting
container reports no port bindings, which the loopback-pinned test reads.

# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-196. The service leg graduates to per-service identity: Keycloak client-credentials JWTs, azp-stamped

- **Status:** Proposed
- **Increment:** 7.18
- **Date:** 2026-10-23

**Decision.** DD-193's service leg proved _that a writer holds the shared
secret_, not _which writer_ — a leaked secret forges un-attributed service
telemetry forever. The graduable headless producers now mint their own
Keycloak identity: four confidential service-account clients
(`otel-postgres`, `otel-keycloak`, `otel-elasticsearch`, `otel-atlas-server`)
on the `otel-ingest` default scope (the same `aud: otel-collector` mapper as
the browser leg), the shared dev client secret carried as an
`${OTEL_INGEST_CLIENT_SECRET}` placeholder in the realm import (the dev-users'
pattern). The collector's `otlp/services` receivers (gRPC 4317 / HTTP 4319)
swap `bearertokenauth` for the **same `oidc` extension** the browser leg uses
— one issuer, one validator, both legs (the contrib image has no
`compositeauth`, so a port carries one authenticator: the per-service leg and
the legacy leg are separate ports by construction). The three slice
metrics-pullers present their JWT through the contrib collector's own
`oauth2client` extension (mint/cache/refresh natively, zero custom code,
`restart: on-failure:15` for the DD-195 race, issuer-shaped now). The Atlas
server (Python, logfire) presents its JWT through an in-app refresh seam:
`ClientCredentialsTokenSource` (stdlib urllib, thread-safe cache,
refresh-ahead, header-less export on mint failure = the visible 401) feeding
per-export `headers` into app-owned OTLP exporters wired through logfire's
`additional_span_processors` / `MetricsOptions.additional_readers` — the
static `OTEL_EXPORTER_OTLP_HEADERS` env is dropped, the app owns the OTLP
export (logfire reads it statically; a 60s dev token cannot ride a static
header). Staying on the **legacy leg** (a new `otlp/legacy` pair, gRPC 4320 /
HTTP 4321, `bearertokenauth`, loopback-published): **Keycloak's native
OTLP** — the issuer cannot present a token it has not minted yet at cold boot
(DD-193's chicken-and-egg, now scoped to exactly this) — and the **FastAPI
example** (the same static-header wall as the server, paid at the server
where it earns). Attribution (DD-194 extended): the resource processor
upserts `otel.ingest.client` from the verified token's `azp`, and a
`transform/identity` (resource context) clears `enduser.id` for
service-account pushes (`azp` prefix `otel-`) — human and machine identity
stay distinguishable in Tempo/Prometheus; browser pushes carry
`otel.ingest.client="aurelius"` + `enduser.id=<sub>`, legacy pushes carry
neither (DD-194's empty-upsert rule, unchanged).

**Reason.** DD-193 refused this graduation for four reasons (Keycloak
self-boot, the pullers' client-credentials need, the Python SDK's static
headers, the boot order) — every one has a bounded answer now: the
`oauth2client` extension is the pullers' client-credentials
mint+refresh, the shim is the Python answer, and Keycloak-native — the one
producer with no answer — keeps the shared token on its own leg. Keycloak is
the issuer of record for every credential in the stack (browsers, APIs);
reusing it for services means one validator, one trust story, and the same
`otel-ingest` audience contract on both legs. Per-client attribution
de-anonymizes the shared secret's blast radius: a leaked `otel-postgres`
secret forges only postgres telemetry, visibly.

**Alternatives.** Static JWTs in env (refused — the dev realm mints 60s
tokens; static bearer JWTs expire in a minute, the whole point of
mint+refresh). One leg with two authenticators (refused — contrib 0.162 has
no `compositeauth`; a client-id allowlist inside one OIDC leg was also
refused: the extension verifies credential _type_, not identity, so the
honest posture is credential-typed legs, every push authenticated and
attributed — a user token on the service leg is a curiosity, not a hole).
Per-service dev secrets (deferred — the clients already carry distinct ids,
which is what the stamp and the revocation target use; distinct secrets
rotate per-producer and the realm placeholder machinery multiplies; prod
deployments inject per-client secrets, the realm import supports it as-is).
A mint sidecar for the Python producers (refused — a sidecar adds a boot
unit per app and a localhost hop; the shim is ~100 stdlib lines with a unit
suite, and the server owns its telemetry the way it owns its store). A
client-credentials file credential source (the OTel spec's
`credentials-file` shape, not implemented in the Python SDK) — the shim is
its stdlib form (watch this: upstream, delete the shim). Permissive-issuer
boot windows for Keycloak-native (refused — an unauthenticated window at
cold boot reopens DD-193's door). Dropping Keycloak-native OTLP (refused —
the IdP's own traces/logs are first-class telemetry for an auth-gated
platform; the puller covers its DB metrics only).

**Consequences.** The dev stack's ingest surface is five loopback-published
ports (4317/4319 per-service OIDC, 4318 browser OIDC, 4320/4321 legacy
shared). Keycloak boot is now load-bearing for the per-service leg the same
way it is for the browser leg: the pullers and the server 401 until the
issuer answers (restart policies + refresh-ahead carry them; DD-195's
collector restart covers the collector itself). The collector's
`enduser.id=""` for services (was DD-193: `sub`-shaped UUID on service
pushes under the DD-194 stamp) is a **label change** for the dashboards:
service series move to `enduser_id=""` + `otel_ingest_client=<id>`; the
dev-stack dashboards' queries ride this increment. The shared ingest token
survives for exactly two producers (Keycloak-native, FastAPI example) — the
legacy leg retires when a gRPC-native producer can present a JWT (a Quarkus
bearer-header hook) and the example app adopts the shim pattern. Realm
re-import rotates the dev client secret: every `.env.enc` carrying it
re-encrypts in the same PR (the DD-193 `otel-ingest` note, extended). e2e:
the webapp suite mints a service token (client_credentials grant, the
`otel-atlas-server` client) beside the 7.17 `user_token` fixture;
`test__collector_accepts_the_shared_ingest_token` moves to the legacy port;
the loopback-pin test's socket set grows to 4317–4321.

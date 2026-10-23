# 7.17 Collector ingest auth

- **Status:** in progress
- **Pull request:** [\#119](<https://github.com/aureliusenterprise/aurelius-atlas/pull/119>)
- **Records:** DD-103 (the two-leg ingest proof: user JWTs for browsers, a shared token for services); extends ADR 039 (TLS proves the channel, the credential proves the writer) and ADR 034 (the one collection point); relies on SHL-11 (the proxy paths), SHL-14 and SPL-11 (the telemetry the proxies carry), ESD-06 (the puller sidecars), APC-05/APC-06 (the login the browser leg gates on)

## Scope

The OTel collector's OTLP receivers stop accepting anonymous writes. It delivers:

- Two ingest legs on `dev/observability`'s collector, each with its own proof of the writer (DD-103):

  - the **browser leg** (HTTP 4318) authenticates the signed-in user through the collector's `oidc` extension: Keycloak issuer, signature, and the `otel-collector` audience. A push with no token, a token from another issuer, or a non-JWT credential is answered 401;
  - the **service leg** (gRPC 4317, HTTP 4319) requires the shared ingest token through `bearertokenauth`: a push without it is answered 401 / `Unauthenticated`.
- The Keycloak realm's `otel-ingest` client scope, on the `aurelius` client's default scopes: its audience mapper stamps `aud: otel-collector` on user tokens (`azp` stays `aurelius`, so the APIs' azp-or-aud validation is unaffected).
- Delivery per producer class:

  - browsers attach their own access token through the OTLP exporters' `headers` factory (the OTLP transport rides XHR/fetch outside Angular's HttpClient, so the bearer interceptor cannot cover it); the live `Keycloak` client attaches in an app initializer, and the factory refreshes per export. The seam is shared, not per-app: `createAureliusOtelIngestAuth` in `aurelius-atlas-observability` (the webapp and the example app wire the same seam). The webapp's and the example app's `/otel/` proxies pass the `Authorization` header through untouched — their config, CSP (`connect-src 'self'`) and the SDK's endpoint wiring are unchanged;
  - server-side exporters (Atlas server, FastAPI example, Keycloak) present the shared token through the standard `OTEL_EXPORTER_OTLP_HEADERS` env var, and the slice puller sidecars (postgres, keycloak-infra, elasticsearch) through their exporter's `headers` block — all on the service leg (4317 gRPC / 4319 HTTP).
- The collector's host publishes pinned to loopback (4317/4318/4319), the prometheus exporter's publish (:9464) dropped — Prometheus scrapes it inside the compose network.

It explicitly does not deliver: per-service identities on the service leg (one shared secret for headless writers; Keycloak-JWT ingest for them stays a future option, DD-103), pre-login browser telemetry (the login is the telemetry gate — accepted, DD-103), token rotation machinery, production deployment manifests, or auth on the collector's internal telemetry (:8888, scraped in-network).

## Semantics

| Id | Rule |
| --- | --- |
| CIA-01 | The collector's OTLP receivers require a credential. The browser leg (4318) answers 401 to a push with no token, a token from an issuer it does not trust, a token without the `otel-collector` audience, or a non-JWT credential (the service token), and accepts a user token the issuer minted. The service leg (4317/4319) answers 401 / `Unauthenticated` without the shared ingest token, and accepts with it. TLS stays as ADR 039 states it — the credential stacks on the verified channel, it does not replace it. |
| CIA-02 | The browser's credential is its own user token: the SPA attaches it through the OTLP exporters' `headers` factory (per export, refreshed), and the `/otel/` proxies pass `Authorization` through untouched — a push with a user token through the webapp/example origin reaches the collector authenticated, a token-less push comes back 401 (the proxy injects nothing). SHL-11's forwarding (prefix stripped) and the CSP (`connect-src 'self'`) are unchanged. |
| CIA-03 | The collector publishes 4317/4318/4319 on 127.0.0.1 only, and no host publish for the prometheus exporter; producers inside compose stacks reach it over service DNS, never through a published port. |
| CIA-04 | Every server-side producer presents the shared token on the service leg: the Atlas server, the FastAPI example, Keycloak's native OTLP, and the three metrics-puller sidecars keep exporting (their telemetry keeps flowing to the collector). |
| CIA-05 | Browser telemetry is attributed: the collector's OIDC receiver resolves the token's `sub`, so a user's OTLP push carries that user's identity and a forged push is attributable to the account that minted the token. |

## Java origin

None. Apache Atlas 2.4.0 ships no OpenTelemetry collector: its telemetry is Dropwizard metrics on the server's own REST port (DV-01's surface, out of scope here). The collector is Aurelius's own architecture (ADR 034); this increment hardens its ingest.

## Deviations

None against Apache Atlas (no Atlas behaviour is touched; the increment is platform-side). The deliberate posture choices — user JWTs on the browser leg over a shared secret, a shared secret on the service leg over per-service identity, the accepted loss of pre-login telemetry, loopback pinning — are recorded in DD-103, not in `deviations.md` (which tracks Atlas-parity deltas).

## Acceptance

- e2e (`nx e2e aurelius-atlas-webapp -c ci`, `nx e2e aurelius-atlas-frontend-example -c ci`):

  - `test__otel_proxy_forwards_to_the_collector` — a push carrying a real user token through the proxy reaches the collector (SHL-11 forwarding, CIA-02)
  - `test__otel_proxy_passes_authorization_through` — a token-less push through the proxy is the collector's 401, proving the proxy injects nothing (CIA-01, CIA-02)
  - `test__collector_rejects_unauthenticated_ingest` — a direct `POST /v1/traces` to the collector's published browser-leg port with no token answers 401, and the CA-verified TLS handshake to the same port succeeds (CIA-01)
  - `test__collector_accepts_a_user_token_on_the_browser_leg` — the same POST with a Keycloak-minted user token (the realm's password grant, the `otel-ingest` audience) answers 2xx (CIA-01, CIA-05, the positive control)
  - `test__collector_stamps_the_user_onto_the_telemetry` — a probe span pushed with a user token comes back from Tempo with the token's `sub` on its resource attributes as `enduser.id` (trace-by-id read-back, `GET /api/traces/<id>?encoding=json`): the identity rode the data into the queryable backend (CIA-05, DD-105; webapp suite)
  - `test__collector_rejects_the_shared_token_on_the_browser_leg` — the service credential on the browser leg answers 401: the legs stay distinct proofs (CIA-01)
  - `test__collector_accepts_the_shared_ingest_token` — the service leg (4319) accepts the shared token (CIA-01, CIA-04)
  - `test__collector_publishes_are_loopback_pinned` — the published sockets bind 127.0.0.1 (CIA-03)
  - `test__producers_keep_flowing_with_the_token` — accepted OTLP exports reach the collector within the suite window, proving the server-side producers present the token (CIA-04; additionally proven by every producer keeping its `nx serve`/e2e runs green — Grafana's stack dashboard shows the pullers and Keycloak flowing)
- Unit (vitest, `aurelius-atlas-observability`): `createAureliusOtelIngestAuth` sends the bearer token of an authenticated session, nothing for a signed-out one or before the client attaches, and the current token when refresh fails (CIA-02, DD-103).
- Run: the dev stack (`nx up aurelius-atlas-dev-observability`) plus the producer slices; `curl --cacert dev/observability/certs/ca.pem` to `https://127.0.0.1:4318/v1/traces` answers 401 with no header and with the service token, 2xx with a user token; `https://127.0.0.1:4319/v1/traces` answers 401 with no header, 2xx with the service token.

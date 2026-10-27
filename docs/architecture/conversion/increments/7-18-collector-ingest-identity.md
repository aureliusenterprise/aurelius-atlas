# 7.18 Collector ingest identity

- **Status:** in progress
- **Pull request:** [#119](https://github.com/aureliusenterprise/aurelius-atlas/pull/119)
- **Records:** DD-196 (per-service ingest identity: Keycloak client-credentials
  JWTs on the service leg, azp-stamped), DD-202 (one issuer world: producers
  mint on the TLS listener, the collector validates both); supersedes the
  service-leg half of DD-193 (user JWTs on the browser leg, the loopback
  pinning, and the shared-token mechanism all stand); extends ADR 039 and
  ADR 034; relies on CIA-01..05 (7.17 — the two legs, the OIDC extension, the
  `otel-ingest` scope, the DD-194 stamping, the DD-195 boot race)

## Scope

The service leg of 7.17 (DD-193) proved _that a writer holds the shared
secret_; it did not prove _which writer_ wrote. This increment gives every
graduable headless producer its own Keycloak identity — a
client-credentials JWT, audience `otel-collector`, minted for a dedicated
realm client — so a forged service push is attributable to the one client
whose secret leaked, and the collector stamps which producer sent every
telemetry push. It delivers:

- Four confidential realm clients on `aurelius`'s model —
  `otel-postgres`, `otel-keycloak`, `otel-elasticsearch`, `otel-atlas-server`
  — service accounts only (no flows), the `otel-ingest` scope as a default
  client scope (the same `aud: otel-collector` mapper as the browser leg),
  the shared dev client secret `${OTEL_INGEST_CLIENT_SECRET}` placeholder in
  the realm import (the dev-users' pattern, `replace-placeholders`).
- The collector's **per-service leg**: `otlp/services` (gRPC 4317 + HTTP 4319)
  swaps `bearertokenauth` for the **`oidc` extension** (same extension, CA,
  audience as the browser leg — one validator, both legs). The extension's
  `providers` list accepts **both** dev Keycloak listeners (DD-202: a token's
  `iss` is the listener that minted it; every automated producer mints at the
  TLS `:8443` listener, the plaintext `:8080` provider stays for the human
  dev browser, ADR 039).
  A new **`otlp/legacy`** receiver pair (gRPC 4320 + HTTP 4321,
  `bearertokenauth`, loopback-published) keeps 7.17's shared-token
  mechanism for the producers that cannot present a Keycloak JWT (below).
  The contrib image has no `compositeauth` extension, so a port carries one
  authenticator — the legs are separate ports by construction (DD-196).
- Graduated producers (per-service JWTs on the per-service leg):
    - the three slice **metrics-pullers** (postgres, keycloak-metadata,
      elasticsearch) present their client credentials through the contrib
      collector's own **`oauth2client`** extension — mint, cache, refresh
      natively, zero custom code; each puller gains
      `restart: on-failure` (the DD-195 race, now issuer-shaped; unbounded
      per DD-226);
    - the **Atlas server** (Python, logfire 5.2) presents its JWT through a
      small in-app refresh shim: a `ClientCredentialsTokenSource`
      (urllib + cache + refresh-ahead, thread-safe, stdlib-only) feeding
      per-export `headers` through logfire's
      `additional_span_processors` / `MetricsOptions.additional_readers`
      seams (logfire reads the static env headers only; the shim replaces
      the env-driven OTLP export — DD-196).
- Staying on the **legacy leg** (shared token, the refused half of DD-193's
  graduation, now scoped to exactly these two):
    - **Keycloak's native OTLP** — the issuer cannot present a token it has
      not minted yet at cold boot (the chicken-and-egg DD-193 named);
    - the **FastAPI example** — the same static-header/60s-token wall as the
      server, for an example app; the shim was built for the server, where
      it pays.
- Attribution (`enduser.id` DD-194, extended): the resource processor
  stamps `otel.ingest.client` from the verified token's `azp` claim; a
  `transform` clears `enduser.id` on service-account pushes (`azp` prefixed
  `otel-`) so human and machine identity stay distinguishable in Tempo and
  Grafana. The browser leg stamps `otel.ingest.client="aurelius"`.

It explicitly does not deliver: per-service identity for Keycloak-native
OTLP or the FastAPI example (DD-196, above), token rotation machinery (a
leaked dev secret rotates by re-import + `.env.enc` bump), a client→leg
allowlist on the OIDC extension (the extension verifies credential _type_,
not identity: a user token on the service leg is accepted and stamped
`azp=aurelius` — every push stays authenticated and attributed, CIA-08),
per-producer secrets in dev (one shared dev client secret, the clients
differ by id), production manifests, or auth on the collector's internal
telemetry.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CIA-06 | The per-service leg (4317 gRPC / 4319 HTTP, OIDC) rejects a push with no token, the shared ingest token, a token from an untrusted issuer, or a token without the `otel-collector` audience (401 / `Unauthenticated`), and accepts a client-credentials JWT minted for an `otel-*` realm client.                                                                                                                                            |
| CIA-07 | Every graduated producer presents its own client's JWT: the three pullers (their `oauth2client` extension) and the Atlas server (the refresh shim) keep exporting through the suite windows — a producer whose client id, secret, or token URL is misconfigured exports nothing (401 at the receiver, visible in its logs).                                                                                                                 |
| CIA-08 | The legs are credential-typed, not identity-typed: the shared token never reaches an OIDC leg (401) and a JWT never reaches the legacy leg (401); a user token presented on the service leg is accepted and stamped `azp=aurelius` (accepted posture: authenticated + attributed is the bar, every push carries its writer).                                                                                                                |
| CIA-09 | The collector stamps the verified writer: service-account pushes carry `otel.ingest.client` = the client id and `enduser.id=""`; user pushes carry `otel.ingest.client="aurelius"` and `enduser.id=<sub>`; legacy-leg pushes carry neither (empty upsert, DD-194's rule, unchanged).                                                                                                                                                        |
| CIA-10 | The legacy leg (4320 gRPC / 4321 HTTP, `bearertokenauth`) is loopback-published like every OTLP port (CIA-03 extended); Keycloak-native and the FastAPI example keep exporting on it with the shared token (CIA-04's surviving half).                                                                                                                                                                                                       |
| CIA-11 | The OIDC legs (browser + per-service) accept a token from **either** dev Keycloak listener — the TLS `:8443` `iss` every automated producer mints at (DD-202), and the plaintext `:8080` `iss` the human dev browser carries (ADR 039) — and reject a token from any other issuer (401). The mint target is fixed in each producer's compose/env as a literal, never suite-flipped, so no suite start-order can starve another's telemetry. |

## Java origin

None. Apache Atlas 2.4.0 ships no OpenTelemetry collector (7.17's finding,
unchanged); the increment is platform-side.

## Deviations

None against Apache Atlas (no Atlas behaviour is touched). The posture
choices — Keycloak as the service-identity issuer, the shared-token legacy
leg for the un-graduable producers, one shared dev client secret, the
credential-typed legs — are recorded in DD-196.

## Acceptance

- e2e (`nx e2e aurelius-atlas-webapp -c ci`, `nx e2e aurelius-atlas-frontend-example -c ci`):
    - `test__collector_accepts_a_service_jwt` — a client-credentials JWT
      (the e2e Keycloak, `otel-atlas-server`) pushed to 4319 answers 2xx,
      and the probe span reads back from Tempo stamped
      `otel.ingest.client=otel-atlas-server` with `enduser.id=""` (CIA-06,
      CIA-07, CIA-09 — the webapp suite, Tempo-wired)
    - `test__collector_rejects_the_shared_token_on_the_service_leg` — the
      shared token on 4319 answers 401 (CIA-06, CIA-08)
    - `test__collector_rejects_a_jwt_on_the_legacy_leg` — a service JWT on
      4321 answers 401 (CIA-08)
    - 7.17's browser-leg tests (`test__otel_proxy_*`,
      `test__collector_rejects_unauthenticated_ingest`,
      `test__collector_accepts_a_user_token_on_the_browser_leg`,
      `test__collector_rejects_the_shared_token_on_the_browser_leg`,
      `test__collector_stamps_the_user_onto_the_telemetry`) — unchanged:
      the browser leg is untouched

> [!NOTE]
> Four dev-posture tests this increment's acceptance named —
> `test__collector_accepts_the_dev_plaintext_issuer` (CIA-11),
> `test__collector_accepts_the_shared_ingest_token` (CIA-10),
> `test__collector_publishes_are_loopback_pinned` (CIA-10, CIA-03) and
> `test__producers_keep_flowing_with_the_token` (CIA-07, CIA-10) — were
> removed by DD-228: they asserted the dev stack's deployment posture
> (the plaintext :8080 listener, the loopback publishes, dev puller liveness),
> not behaviour the product ships. The per-service leg's JWT proofs
> (CIA-06/07/09 via `test__collector_accepts_a_service_jwt`) and the leg
> separation (CIA-08) stay in the webapp suite; the two-listener acceptance
> (CIA-11) rides the collector's shipped OIDC config and review.

- Unit (pytest, server): `ClientCredentialsTokenSource` mints with
  client_secret_basic, caches until refresh-ahead, refreshes per expiry,
  survives mint failure (export proceeds header-less, the 401 path);
  the exporters attach the bearer header per export (CIA-07).
- Run: the dev stack plus producers; `curl` matrix on the CA-verified TLS:
    - 4317/4319: none→401, shared→401, service JWT→200
    - 4320/4321: none→401, shared→200, JWT→401
    - Grafana: the pullers' and the server's series keep flowing;
      Tempo resource search `{ .resource["otel.ingest.client"] =
"otel-postgres" }` (backend blocks; DD-194's live-store note).

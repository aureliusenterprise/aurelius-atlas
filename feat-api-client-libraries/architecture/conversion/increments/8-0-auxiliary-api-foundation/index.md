# Increment 8.0 — Auxiliary API Foundation

| Field | Value |
| --- | --- |
| Status | accepted |
| Author | Aurelius Atlas maintainers |
| Date | 2026-07-19 |
| ADRs | 055 (auxiliary APIs are a named data surface), 036 (per-app OTel exporter chain), 034 (dev Keycloak), 051 (increments) |
| Design log | DD-196 (extended here), DD-197 (per-service ingest identities), DD-132 |

## Objective

The legacy Aurelius dashboard consumes small auxiliary APIs alongside the Atlas metadata API (ADR 055). Increments 8.1–8.3 ship them as FastAPI apps. This increment is the **shared foundation** they all need, extracted from the server so it is written and tested once:

- **`aurelius-atlas-otel`** — the collector ingest leg (DD-196's client-credentials token source + OTLP pipeline), moved out of `aurelius-atlas-server` so every service gets traces/logs/metrics to the collector with its own Keycloak identity (DD-197).
- **`aurelius-atlas-auth`** — the OIDC verifier the example app prototyped (JWKS refresh, breaker, audience/role checks), ported into a library the auxiliary apps import.
- **Keycloak** — one `otel-<service>` ingest client per auxiliary app.

No HTTP endpoint is added by this increment; the surface rules below govern the two libraries' behaviour, which is the contract the 8.x apps build on.

## Scope

In scope: `libs/python/aurelius-atlas-otel`, `libs/python/aurelius-atlas-auth`, `dev/keycloak/import/master.json`, the server's app wiring to the new otel lib.

Out of scope: the auxiliary apps themselves (8.1–8.3), the server's lineage feed (5.1), CSRF (the auxiliary APIs are same-token bearer APIs like the metadata API — the server's ADR 039 cookie/CSRF flow is server-scope; noted in DD-197).

## Contracts and Rules

### Foundation behaviour

| ID | Rule | Java / legacy source | Enforced by | Deviation |
| --- | --- | --- | --- | --- |
| AUX-01 | An OTLP exporter's session acquires a `<azp> for aud=otel-collector` client-credentials token — the service's `otel-<service>` Keycloak identity, DD-196 shape — and attaches it as a bearer header to every export request | (Aurelius: DD-196, extended by DD-197) | `test__export_request_carries_the_bearer_token` | — |
| AUX-02 | The token is refreshed ahead of expiry, cached across requests, and refreshed once (with the old token dropped) on a 401/403 | (Aurelius: DD-196) | `test__token_is_cached_and_refreshed_ahead_of_expiry` `test__a_401_forces_one_refresh_and_a_retry` | — |
| AUX-03 | When no ingest credentials are configured, the pipeline exports to the console only — dev mode, never a broken collector leg | (Aurelius: server `app.py`, DD-197) | `test__console_only_without_config` | — |
| AUX-04 | A verified token's roles are the realm roles plus the roles of the service's own audience only: Keycloak namespaces client roles under `resource_access.<audience>`, so another service's roles never grant access here (DD-132's rule, now library-wide) | (Aurelius: example app, DD-132) | `test__an_external_clients_role_does_not_grant_write` `test__an_unprefixed_client_role_does_not_grant_write` `test__realm_roles_apply_under_any_audience` | — |
| AUX-05 | Signature, issuer, and expiry are verified against the realm's published keys (kid selected, alg pinned to RS256); the `azp`/`aud` must name the service; the raw-bearer dependency yields the unverified token for forwarding only, never authorisation | (Aurelius: example app) | `test__a_valid_token_is_accepted` `test__a_forged_signature_is_rejected` `test__a_token_from_a_foreign_issuer_is_rejected` `test__an_expired_token_is_rejected` `test__an_unverified_alg_is_rejected` `test__a_token_minted_for_another_audience_is_rejected` `test__require_bearer_yields_the_raw_token_for_forwarding` `test__a_missing_credential_is_rejected` | — |

### Non-negotiables (workspace-wide, restated for 8.x)

CIA-07 (every exporter leg carries the per-service ingest token, defined in 7.18's spec) is enforced here by `test__export_request_carries_the_bearer_token` in the moved suite; the rule id keeps its home in `7-18-collector-ingest-identity.md`.

## Data contracts

- `aurelius_atlas_otel.ingest.build_otlp_pipeline(...) -> IngestPipeline` with keyword args `endpoint`, `service_name`, `deployment_env`, `token_url`, `client_id`, `client_secret`, `ca_file`, `protocol` — verbatim move of the server's `otel_ingest.py`; the server imports it now.
- `aurelius_atlas_auth.auth.KeycloakAuth(AuthConfig(server_url, realm, audience, write_role, ...), http)` — exposes `require_auth` / `require_write` (authorised `AuthUser`) and `require_bearer` (raw token, forwarding only), per AUX-04/AUX-05.
- Keycloak clients `otel-data2model`, `otel-lineage-model`, `otel-validate-entity` join the `otel-collector` audience group (DD-197).

## Test list

- Unit: `libs/python/aurelius-atlas-otel/tests/test__ingest.py` (moved), `libs/python/aurelius-atlas-auth/tests/test__auth.py` (new, fake issuer).
- E2E: none for this increment — the libraries are exercised end-to-end by the 8.1–8.3 app e2e suites against the shared dev Keycloak and collector.
- Parity: none — the foundation ports Aurelius mechanisms (DD-196/DD-197/DD-132), not Atlas 2.4 behaviour; the example app's auth tests are the reference.

## Acceptance criteria

- [x] Every rule id above names a unit test (ADR 049 — `aurelius-atlas-trace check` green).
- [x] The server keeps its collector leg through the lib (`nx test aurelius-atlas-server -c ci`).
- [x] Keycloak import stays valid JSON; the three clients appear with the collector audience.
- [x] Ruff, pyright, prettier, commit checks.

## Delivery

- Branch: `feat/aux-apis-foundation` (PR 1 of the 8.x chain).
- M6: this is shared plumbing for the ADR 055 data surface; the ADR 052 gate applies at 8.1–8.3, where dashboard-visible behaviour lands.

## Open questions

- Ingest identity granularity: one `otel-<service>` client each (DD-197) vs one shared client — chosen per-service for least privilege; secrets scale with service count (accepted).
- CSRF for the auxiliary APIs: deferred to the webapp increment that serves them; the APIs are bearer-first (CORS + same token), matching the metadata API.

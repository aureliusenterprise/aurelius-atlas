# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-197. The auxiliary APIs share one foundation: the OTel and auth libs

Each auxiliary app gets its own ingest client (increment 8.0).

- **Status:** Proposed
- **Increment:** 8.0
- **Date:** 2026-11-08

**Decision.** The auxiliary API apps of ADR 055 (8.1–8.3) do not each
re-implement the plumbing. Two libraries carry it, both extracted from code
this workspace already runs and tests:

- `libs/python/aurelius-atlas-otel` — DD-196's ingest mechanism (the
  client-credentials token source with refresh-ahead + 401-retry, the
  OTLP pipeline builder, console-only dev mode) moves verbatim out of
  `aurelius_atlas_server/otel_ingest.py` with its six tests. The server
  imports the lib; every future service gets the same collector leg by
  configuring three settings. The per-service identity story extends:
  `otel-data2model`, `otel-lineage-model` and `otel-validate-entity` join the
  `otel-<service>` confidential-client family on the `otel-ingest` scope
  (DD-196's audience/mapper unchanged), each carrying its own
  `${OTEL_INGEST_CLIENT_SECRET}` placeholder.
- `libs/python/aurelius-atlas-auth` — the FastAPI example's OIDC verifier
  (OIDC discovery + JWKS behind a circuit breaker, kid-pinned RS256 verify,
  issuer check, `azp`∪`aud` audience match, realm-roles-plus-own-audience
  roles per DD-132) becomes the workspace's auth library. The auxiliary
  apps consume it as `require_auth` / `require_write` dependencies; the raw
  bearer dependency exists for forwarding only, never authorisation (AUX-05).

**Reason.** The example app's auth prototype is the workspace's only
verified OIDC implementation, and DD-196's ingest shim is the only verified
service-identity implementation — a third FastAPI app copying either file is
three copies of a security path (049's test-naming rule argues the same:
one named test per rule, not three near-identical ones). Extraction is
cheaper now than convergence later, and both libs ship with the server's
green suites. Per-service ingest clients (vs one shared auxiliary client):
DD-196's least-privilege reasoning applies verbatim — a leaked
`otel-data2model` secret forges only data2model telemetry, visibly.

**Alternatives.** Copy-paste per app (refused — three drift-prone copies of
auth + ingest). One shared ingest client for all auxiliary apps (refused —
DD-196 rejected exactly this for the server fleet). Put auth inside the
server app and import across apps (refused — the server is an app, not a
lib; apps importing apps inverts the dependency graph and drags the store).
A dedicated `aurelius-atlas-fastapi-base` app template with auth+otel baked
in (deferred — premature until three real consumers exist; the two libs
compose into the 8.x apps with ten wiring lines each, and a template can
formalise from those).

**Consequences.** The server's `app.py` gains one import
(`aurelius_atlas_otel`) and loses `otel_ingest.py`; its six CIA-07 tests
move to the lib unchanged (the spec-file rule ids ride along: the tests
cite CIA-07, defined in 7.18's spec, unchanged). The Keycloak realm import
grows three clients; realm re-import rotates nothing new (shared dev secret,
DD-196's note). 8.1–8.3 each add: a settings model (env prefix), the app
factory, auth dependencies from the lib, `build_otlp_pipeline` from the
lib, one `otel-<app>` client's secret in `.env.enc`, and their own rule
ids. CSRF stays out of scope: the auxiliary APIs are bearer-first like the
metadata API; the cookie/CSRF story is the webapp increment that serves
them (8.4+).

# Increment 8.3 — validate-entity API

| Field | Value |
| --- | --- |
| Status | accepted |
| Author | Aurelius Atlas maintainers |
| Date | 2026-10-23 |
| ADRs | 055 (auxiliary APIs are a named data surface), 051 (increments), 049 (traceability), 052 (parity cites the reference; here the reference is Aurelius source) |
| Design log | DD-108 (foundation), DD-120 (provider/route layout), DD-110 (test env), DD-112 (the mock body as module data, the injectable verifier), DV-14 (the app ships as the legacy mock) |

## Objective

Port the legacy Aurelius `m4i-validate-entity` service — the entity governance-quality endpoint the webapp's editor calls while a record is being edited — to a FastAPI app: `apps/aurelius-atlas-validate-entity`.

The legacy service **is a mock** (DV-14): `POST /` accepts the entity, never reads it, and answers a fixed governance-quality document — four cards (`dataEntity`, `definition`, `domainLead`, `name`), each a list of `gov_quality`-shaped items with a compliance flag. The browser's editor renders those cards; the compliance verdicts are canned. Increment 8.3 ships that mock contract verbatim, with the workspace's auth (DD-108) and observability (DD-107): the browser contract is kept, real validation is a future server rule (DV-14).

`POST /` answers `200 application/json` with the mock document for any request body; the body is not parsed (the legacy ignores it, and the port keeps that). `GET /` requires a valid Keycloak bearer token, verified for this app's audience — not the legacy's `transparent=True` pass-through (DV-24). The app has no upstreams: unlike 8.2's chain, nothing is forwarded.

The legacy is a Flask app on `m4i_backend_core` (gunicorn, `WSGI_PORT` 7200). The port follows the 8.x app conventions: FastAPI, the shared `aurelius-atlas-auth` verifier, app-owned OTel export, TLS, the `21000`-series port (21003).

## Scope

In scope: the app (settings, app factory, `POST /`, liveness), the mock document as module data, unit tests, a parity scenario, container and e2e (Keycloak-protected).

Out of scope: real governance validation (DV-14 — a future server rule), the webapp governance cards (7.x track), the `gov_quality` ElasticSearch engine the mock's `_meta.engine` name echoes (the document names it; the app does not call it).

## Contracts and Rules

The reference for every rule is the Aurelius source (ADR 055 R4): `backend/m4i-validate-entity/m4i_validate_entity/m4i_validate_entity.py` (`mock_response`, the `output` dict), and the webapp caller `libs/atlas/api/src/lib/gov-quality/gov-quality-api.service.ts` (`GovQualityApi.validateEntity` — `POST validate_entity` with the entity, `EntityValidationResponse` the cards consume) via `apps/atlas/proxy.conf.json` (`/validate_entity` → the service).

### The validation endpoint

| ID | Rule | Legacy source | Enforced by | Deviation |
| --- | --- | --- | --- | --- |
| VE-01 | `POST /` answers `200 application/json` with the fixed mock document verbatim, for any request body — the entity is accepted and ignored (the mock's whole contract, DV-14); malformed/absent bodies answer the same document | `mock_response()` (`json.dumps(output)`, the body never read) | `test__the_mock_document_is_returned_verbatim` `test__any_body_is_accepted` | — |
| VE-02 | The mock document is the legacy `output` dict ported verbatim as data: the four keys `dataEntity`/`definition`/`domainLead`/`name`, each `{items: [one gov_quality-shaped item], isNonCompliant}`; the items carry the legacy's `doc-…` ids, `raw` values, `Attribute - <key>` names, and `_meta.engine` `atlas-dev-gov-quality` | the `output` dict | `test__the_mock_document_is_the_legacy_output` | — |
| VE-03 | `POST /` requires a valid Keycloak bearer token verified for this app's audience (`aurelius-atlas-auth`, AUX-05) — not the legacy's transparent pass-through; a missing/invalid token is `401`; nothing is forwarded (no upstreams) | `@requires_auth(transparent=True)` (no validation) | `test__a_missing_token_is_rejected` `test__a_token_minted_for_another_audience_is_rejected` | DV-24 (full validation, DD-108 convention) |
| VE-04 | `GET /liveness` answers `204` without auth (the container healthcheck) | `m4i_backend_core/shared::register` — `GET /heartbeat` → `200 {"success": true}` | `test__liveness_needs_no_token` | DV-25 (the 8.x route/status, not `/heartbeat` 200) |
| VE-05 | Settings (env prefix `AURELIUS_ATLAS_VALIDATE_ENTITY_`): port defaults to 21003, TLS is configured by the cert/key pair, the auth block is required (DD-108 shape) | `conf.py` / the shared core's settings | `test__the_settings_are_read_from_prefixed_variables` (settings suite) | — |

### The mock document shape

`{<key>: {items: [{result: {raw}, dataqualitytype: {raw: "attribute"}, usedattributes: {raw: [key]}, name: {raw: "Attribute - <key>"}, compliant: {raw: "0"|"1"}, _meta: {engine, score, id}, id: {raw}}], isNonCompliant}}` — the `AppSearchResult<GovQualitySearchObject>` shape the webapp's governance cards parse. The document is a constant, not generated from the entity: byte equality is the contract (VE-01/VE-02), which makes the parity scenario a whole-body comparison with no volatile fields.

## Data contracts

- `POST /` (any body) → `200` the mock document / `401` with `{"errorCode", "errorMessage"}` (VE-01/VE-03).
- `GET /liveness` → `204` (VE-04).
- `aurelius_atlas_validate_entity.mock.MOCK_VALIDATION` — the document, as module data.
- `create_app(settings, auth=None)` — `auth` is the shared verifier (injectable for tests, DD-112).
- Settings (env prefix `AURELIUS_ATLAS_VALIDATE_ENTITY_`): `host`, `port` (21003), `log_level`, `tls_cert_file`/`tls_key_file`, `auth_server_url`, `auth_realm`, `auth_audience`, `auth_ca_file`, `otel_token_url`, `otel_client_id` (`otel-validate-entity`), `otel_client_secret`, `otel_endpoint`, `otel_ca_file`.

## Deviations (recorded in `deviations.md`)

- **DV-24**: the endpoint fully verifies the bearer token for its audience (AUX-05, DD-108), not the legacy's `transparent=True` pass-through (VE-03; DV-23's pattern, with no forwarding — the app has no upstreams).
- **DV-25**: the healthcheck is `GET /liveness` → `204`, not the legacy core's `GET /heartbeat` → `200 {"success": true}` (VE-04) — the route, status and empty body of every 8.x app's container healthcheck (DD-108 family).

## Test list

- Unit: `apps/aurelius-atlas-validate-entity/tests/test__aurelius_atlas_validate_entity_app.py` (VE-01/02/03/04 wiring on the fake issuer, the mock document verbatim), `test__aurelius_atlas_validate_entity_settings.py` (VE-05), `test__aurelius_atlas_validate_entity_providers_auth.py`/ `test__…_providers_telemetry.py`/`test__…_routes.py` (the DD-120 providers and route factories, on the fake issuer), `test__…___main__.py`.
- Scenario (parity, read from Aurelius source): `scenarios/validation/ mock.scenario.yaml` — the caller's entity payload, `POST /` → the full mock document, byte equality (no volatile: the body is a constant).
- E2E: `e2e/` — real container, Keycloak-minted token (the browser's own: the public `aurelius` client, the caller's audience, AUX-04); 401 anonymous, 200 mock, liveness.

## Acceptance criteria

- [ ] Every rule id names a test (ADR 049 — `aurelius-atlas-trace check` green).
- [ ] The mock document travels byte-for-byte to a real browser-shaped caller (e2e).
- [ ] Ruff, pyright, prettier, commit checks; `nx test`/`nx e2e` pass.

## Delivery

- Branch: `feat/aux-apis-validate-entity` (PR 4 of the 8.x chain, on 8.2).
- M6: the editor's governance cards render the mock's verdicts once the 7.x webapp track points at this app; the cards are unchanged (ADR 055).

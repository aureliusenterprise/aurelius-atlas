# Increment 8.2 — lineage-model API

| Field      | Value                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status     | accepted                                                                                                                                                     |
| Author     | Aurelius Atlas maintainers                                                                                                                                   |
| Date       | 2026-10-23                                                                                                                                                   |
| ADRs       | 055 (auxiliary APIs are a named data surface), 051 (increments), 049 (traceability), 052 (parity cites the reference; here the reference is Aurelius source) |
| Design log | DD-108 (foundation), DD-110 (test env), DD-111 (proxy app: injectable upstream, canned-file fixture Atlas), DV-16 (stubbed data path)                        |

## Objective

Port the legacy Aurelius `m4i-lineage-model` service — the lineage-graph API
the webapp's lineage screen calls — to a FastAPI app:
`apps/aurelius-atlas-lineage-model`.

`GET /` takes `guid` (required), `depth` (default 3) and `direction` (default
`BOTH`), fetches the entity's lineage from an Atlas metadata API
(`GET {atlas_base_url}/v2/lineage/{guid}`), flattens the lineage relations
into the 12-column archimate rows, and POSTs them with the fixed lineage
rules to data2model `/extract` (8.1), returning that response body verbatim —
the `{model, metadata}` document the lineage screen consumes. The chain is
`webapp → lineage_model → data2model /extract`.

Per DV-16 the **data path is stubbed until the server's lineage feed (5.1)**:
the Atlas base URL is a setting, no increment blocks on 5.1, and the tests
use canned lineage fixtures. The **caller's bearer token is forwarded** to
both upstream calls — the legacy's token-passing design (the caller is the
browser's own token; 8.1 records why that makes `aurelius` the audience).

The legacy is a Flask app on `m4i-atlas-core` (`get_lineage_by_guid`,
`LineageInfo` dataclasses, `requests.post` to data2model). The port follows
DD-109: pydantic models parse the upstream lineage at the boundary, rows are
plain dicts, and the HTTP client is injectable for tests (DD-111).

## Scope

In scope: the app (settings, app factory, `GET /`, liveness), the lineage
models and flattening, the fixed rules document, unit tests, a parity
scenario, container and e2e (Keycloak-protected; the real data2model
container; a canned-file fixture Atlas).

Out of scope: the Atlas lineage feed itself (5.1 — the setting points at it),
the webapp lineage screen (7.x track), the legacy `aiocache` `@cached()` on
the fetch (a dev convenience; the screen refetches on navigation — no cache),
the `m4i-atlas-core` library (only the lineage fetch is ported, as a local
httpx call).

## Contracts and Rules

The reference for every rule is the Aurelius source (ADR 055 R4):
`backend/m4i-lineage-model/m4i_lineage_model/lineage_model.py`
(`lineage_model`, `fmt_lineage_relation`, the `rules` dict, `process_types`),
`libs/m4i-atlas-core/m4i_atlas_core/api/atlas/get_lineage_by_guid.py`
(path, params), `.../entities/atlas/core/lineage_info/LineageInfo.py`
(camelCase JSON shape), and the webapp caller
`apps/atlas/src/app/search/details/components/lineage-model/lineage-model.service.ts`.

### The lineage endpoint

| ID    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                               | Legacy source                                                                                            | Enforced by                                                                                                                                                                                                                   | Deviation                                                      |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| LM-01 | `GET /` takes `guid` (required), `depth` (int, default 3) and `direction` (`BOTH`/`INPUT`/`OUTPUT`, default `BOTH`); on success it answers `200 application/json` with the data2model body `{model, metadata}` verbatim (the lineage screen's document)                                                                                                                                                                            | `lineage_model()` (`return response.text`)                                                               | `test__the_extract_body_is_returned_verbatim`                                                                                                                                                                                 | —                                                              |
| LM-02 | Each lineage relation flattens to one 12-column row `{id, from_entity_id/name/type, from_process_id/name/type, to_entity_id/name/type, to_process_id/name/type}`: the relation's `relationshipId` is `id`; an endpoint whose `typeName` is in the process family fills its `*_process_*` slots (entity slots null), every other type fills its `*_entity_*` slots (process slots null); values are `guid`/`displayText`/`typeName` | `fmt_lineage_relation`                                                                                   | `test__a_process_endpoint_fills_the_process_slots` `test__an_entity_endpoint_fills_the_entity_slots`                                                                                                                          | —                                                              |
| LM-03 | The process family is the seven legacy `m4i_*_process` type names, ported as data verbatim                                                                                                                                                                                                                                                                                                                                         | `lineage_model.py` `process_types`                                                                       | `test__the_process_family_is_the_legacy_list`                                                                                                                                                                                 | —                                                              |
| LM-04 | The extraction body is `{"data": rows, "rules": LINEAGE_RULES}` with the fixed rules document (4 element, 2 relation, 1 static `lineage_view`/`Lineage`/`archimate_process` view) ported verbatim, POSTed to `{data2model_url}/extract` carrying the caller's bearer token; the fetch is `GET {atlas_base_url}/v2/lineage/{guid}?depth&direction` carrying it too                                                                  | the `rules` dict; `post(... headers={'Authorization': f'bearer {access_token}'})`; `get_lineage_by_guid` | `test__the_extract_request_carries_the_rows_and_fixed_rules` `test__both_upstream_calls_carry_the_callers_token`                                                                                                              | Forwarding is `Authorization: Bearer <token>` (canonical case) |
| LM-05 | An upstream lineage `404` (unknown guid) is answered `204` with an empty body; an upstream lineage `400` is answered `400` (the port adds the Atlas error body)                                                                                                                                                                                                                                                                    | `lineage_model()` 404 → `('', 204)`, 400 → `abort(400)`                                                  | `test__an_unknown_guid_is_204` `test__an_upstream_bad_request_is_400`                                                                                                                                                         | 400 gains the Atlas-shaped error body (DV-18 family)           |
| LM-06 | A lineage whose `relations` are empty is answered `204` with an empty body (no extract call, no empty model)                                                                                                                                                                                                                                                                                                                       | `len(lineage.relations) == 0` → `('', 204)`                                                              | `test__a_lineage_without_relations_is_204`                                                                                                                                                                                    | —                                                              |
| LM-07 | An upstream failure that is not the 404/400 of the lineage fetch — a 5xx, a lineage body naming a guid absent from `guidEntityMap`, a failing `/extract` — is answered `502` with the Atlas error body; a missing `depth`/`direction`/`guid` query problem is `400` with the same body, not a 500 from `int()`/`Enum()`/a literal-`None` guid fetch                                                                                | uncaught `ValueError`/`KeyError`/`ClientResponseError`/`raise_for_status` (Flask 500)                    | `test__an_upstream_server_failure_is_502` `test__a_lineage_with_a_dangling_guid_is_502` `test__a_failing_extract_is_502` `test__an_invalid_direction_is_400` `test__a_non_numeric_depth_is_400` `test__a_missing_guid_is_400` | DV-20, DV-21, DV-22                                            |
| LM-08 | `GET /` requires a valid Keycloak bearer token verified for this app's audience (`aurelius-atlas-auth`, AUX-05) — not the legacy's transparent pass-through; a missing/invalid token is `401`; the token forwarded upstream is the caller's raw token                                                                                                                                                                              | `@requires_auth(transparent=True)` (no validation)                                                       | `test__a_missing_token_is_rejected` `test__a_token_minted_for_another_audience_is_rejected`                                                                                                                                   | DV-23 (full validation, DD-108 convention)                     |
| LM-09 | `GET /liveness` answers `204` without auth (the container healthcheck)                                                                                                                                                                                                                                                                                                                                                             | the shared core module's liveness                                                                        | `test__liveness_needs_no_token`                                                                                                                                                                                               | —                                                              |
| LM-10 | Settings (env prefix `AURELIUS_ATLAS_LINEAGE_MODEL_`): `atlas_base_url` and `data2model_url` are required HttpUrls, port defaults to 21002, TLS is configured by the cert/key pair (DD-108 shape)                                                                                                                                                                                                                                  | `conf.py` required keys `atlas.server.url`, `data2model.server.url`                                      | `test__the_settings_are_read_from_prefixed_variables` (settings suite)                                                                                                                                                        | —                                                              |

### Upstream lineage shape

The fetch consumes Atlas's `v2/lineage/{guid}` camelCase JSON —
`{guidEntityMap: {guid: {guid, typeName, displayText, …}}, relations:
[{fromEntityId, relationshipId, toEntityId}], …}` — parsed as pydantic
models with extra fields ignored (the legacy's `dataclasses_json` shape);
only the fields the flattening reads are declared (DD-109).

## Data contracts

- `GET /?guid=&depth=&direction=` → `200 {model, metadata}` / `204` /
  `400`/`401`/`502` with `{"errorCode", "errorMessage"}` (LM-01..LM-08).
- `GET /liveness` → `204` (LM-09).
- `aurelius_atlas_lineage_model.lineage`: `LineageInfo`, `EntityHeaderLite`,
  `LineageRelation` (pydantic), `PROCESS_TYPES`, `LINEAGE_RULES` (the fixed
  document), `flatten_relations(info) -> list[dict]`.
- `create_app(settings, auth=None, http=None)` — `http` is the upstream
  `httpx.Client` (injectable for tests, DD-111); production builds one with
  a timeout, TLS CA from the auth settings.
- Settings (env prefix `AURELIUS_ATLAS_LINEAGE_MODEL_`): `host`, `port`
  (21002), `log_level`, `tls_cert_file`/`tls_key_file`, `auth_server_url`,
  `auth_realm`, `auth_audience`, `auth_ca_file`, `atlas_base_url`,
  `data2model_url`, `otel_token_url`, `otel_client_id` (`otel-lineage-model`),
  `otel_client_secret`, `otel_endpoint`, `otel_ca_file`.

## Deviations (recorded in `deviations.md`)

- **DV-20**: an invalid `depth`/`direction` is `400`, not the legacy's Flask
  `ValueError` → 500 (LM-07).
- **DV-21**: a missing `guid` is `400`, not the legacy's fetch of the literal
  guid `None` (→ upstream 404 → 204) (LM-07).
- **DV-22**: upstream failures beyond the lineage 404/400 (5xx, dangling
  guid, failing `/extract`) are `502` with the Atlas error body, not uncaught
  exceptions → Flask 500 (LM-07).
- **DV-23**: the endpoint fully verifies the bearer token for its audience
  (AUX-05, DD-108), not the legacy's `transparent=True` pass-through;
  browser tokens (azp `aurelius`) pass both.

## Test list

- Unit: `apps/aurelius-atlas-lineage-model/tests/test__lineage.py` (LM-02..LM-07,
  the flattening, rules, forwarding, upstream statuses on a mock transport),
  `test__app.py` (LM-01/08/09 wiring on the fake issuer),
  `test__aurelius_atlas_lineage_model_settings.py` (LM-10), `test__…___main__.py`.
- Scenario (parity, read from Aurelius source): `scenarios/lineage/graph.scenario.yaml`
  — the caller's fixed rules over the 8.1 scenario's two-relation lineage;
  the canned `/extract` answer is the 8.1-verified model document, so the
  expected body is full equality (no volatile — DV-15 is inside the canned answer).
- E2E: `e2e/` — real container, Keycloak-minted token, the **real**
  data2model container, and a canned-file fixture Atlas (dhi.io Python
  `http.server`, DD-111); 401 anonymous, 200 chain, 204 unknown guid.

## Acceptance criteria

- [ ] Every rule id names a test (ADR 049 — `aurelius-atlas-trace check` green).
- [ ] The forwarded-token chain works end to end (browser token, audience `aurelius`).
- [ ] Ruff, pyright, prettier, commit checks; `nx test`/`nx e2e` pass.

## Delivery

- Branch: `feat/aux-apis-lineage-model` (PR 3 of the 8.x chain, on 8.0).
- M6: the lineage graph renders end to end once the 7.x webapp track points
  at this app; the screen is unchanged (ADR 055).

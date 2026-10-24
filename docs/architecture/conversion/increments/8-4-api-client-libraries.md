# Increment 8.4 — API client libraries

| Field      | Value                                                                                                                                                                                                |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status     | in progress                                                                                                                                                                                          |
| Author     | Aurelius Atlas maintainers                                                                                                                                                                           |
| Date       | 2026-10-23                                                                                                                                                                                           |
| ADRs       | 051 (increments), 049 (traceability), 055 (auxiliary APIs are a named data surface), 036 (per-app OTel exporter chain — unchanged), 050 (the template's example apps are removed, not served here)   |
| Design log | DD-203 (the contract lives in a client library; the app imports it), DD-204 (clients are async httpx, superseded on construction by DD-205), DD-205 (the `httpx.AsyncClient` is provided externally) |

## Objective

Every Python HTTP API in the workspace answers a wire contract today — the server's
Atlas REST routes, `data2model`'s `/extract`, `lineage-model`'s `GET /`, and
`validate-entity`'s `POST /` — and every one of them states that contract **inside
the app that serves it**, or not at all (the server answers `.to_json()` dicts,
`data2model` answers an untyped `dict`, `validate-entity` answers a `dict` constant).
There is no Python client anywhere: `aurelius-atlas-sdk` is utility code, and the
only outbound calls (`lineage-model`'s upstreams) are ad-hoc `httpx`.

This increment gives each API **an accompanying library** that owns the contract —
pydantic models for the requests and responses — **and an API client** for it. The
Angular side has this shape already (`libs/angular/aurelius-atlas-data-access`,
7.3); this is its Python twin. The apps stop being the sole definition site of their
own wire contract: each **imports** the models its client library states, so a
consumer and the server validate against one source of truth (DD-203).

Four libraries, one per API:

| Library                                             | Contract                                                                                                        | Client                 |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `libs/python/aurelius-atlas-server-client`          | the Atlas metadata API the server routes answer (admin, types), plus the Atlas lineage body `v2/lineage/{guid}` | `AtlasClient`          |
| `libs/python/aurelius-atlas-data2model-client`      | `POST /extract`: the rules document in, `{model, metadata}` out                                                 | `Data2ModelClient`     |
| `libs/python/aurelius-atlas-lineage-model-client`   | `GET /?guid=&depth=&direction=` of 8.2                                                                          | `LineageModelClient`   |
| `libs/python/aurelius-atlas-validate-entity-client` | `POST /` of 8.3: the governance-quality document out                                                            | `ValidateEntityClient` |

## Scope

In scope:

- The four libraries, scaffolded per `libs/python/AGENTS.md` and registered in the
  root `pyproject.toml`.
- The **relocation** of each contract's models into its client library (DD-203):
  `ExtractionRequest` and the rule-model family out of `aurelius_atlas_data2model.rules`;
  `LineageInfo`, `EntityHeaderLite`, `LineageRelation` and `Direction` out of
  `aurelius_atlas_lineage_model.lineage`; and the **new** response models the apps
  never had (`ExtractionResponse`, `ValidationResponse`, the admin shapes).
- The four async clients, on the shared client conventions (CL-01..CL-07).
- The apps rewired to import their own contract and, for `lineage-model`, to call
  its upstreams through the clients (its routes become `async def`).
- Unit tests for every public function (`covers`, ADR 049), mkdocstrings pages.

Out of scope:

- `aurelius-atlas-fastapi-example` — a template demo, removed by ADR 050; it keeps
  its in-app `Envelope`/`PaginatedResponse` models.
- `AtlasClient.get_lineage` — the **method** lands with the server's lineage feed
  (5.1), spec-first; only the lineage **models** move here, because 8.2 consumes them.
- Entity/search/discovery server routes (increments 2.x–6.x) — each adds its client
  methods and DTOs as it ships the route, the pattern this increment sets.
- The Angular data-access lib (stays hand-mirrored) and a code generator (openapi →
  pydantic): hand-written, reviewable contracts, parity-guarded (ADR 052).
- Real governance validation (DV-67) and the auth/otel libs (8.0).

## Semantics

Each rule the behaviour must obey, with an id that tests name in
`@pytest.mark.covers(..., rules=["CL-NN"])`.

### The client libraries (all four)

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL-01 | A client is constructed from an externally provided `httpx.AsyncClient` and a token source, and reads no environment variables — the app builds the httpx client from its own settings (TLS, timeout) and passes it in. The client's request paths are **relative to that client's base URL**, so the app's URL passes through as given — a pydantic `HttpUrl`'s `str()`, which ends in a trailing slash, needs no trimming (the libs-python rule, as `aurelius-atlas-auth`). |
| CL-02 | The `httpx.AsyncClient` a client wraps is provided externally, so tests pass one built on a `MockTransport` and no socket opens (the DD-200 seam, made async); whoever builds the httpx client closes it — the API client exposes no close of its own, it borrows the pool, and a `with_token` wrapper shares it and closes nothing.                                                                                                                                          |
| CL-03 | Every request carries `authorization: Bearer <token>` from the token source, on every call — the browser-token-forwarding of 8.2 is one source (a callable yielding the caller's token), not a special case. An **empty** token is the unauthenticated call: no header at all — an empty bearer is not a legal HTTP header value, and the server's open routes (6.1 closes them) must be reachable with an empty source.                                                      |
| CL-04 | A non-2xx answer raises the library's `*ClientError` carrying the status and, when the body parses, the server's `{errorCode, errorMessage}`; a success raises nothing. A 204 on a lineage-model call is the caller's success path, not an error.                                                                                                                                                                                                                             |
| CL-05 | An unreachable upstream (`httpx.RequestError`) propagates as `httpx`'s own error — mapping a transport failure to an HTTP status is the **app's** job (LM-07's DV-80), not the client's.                                                                                                                                                                                                                                                                                      |
| CL-06 | The models are the wire contract: camelCase field aliases on Atlas-shaped bodies (`typeName`, `guidEntityMap`), `extra="ignore"` on what the apps read leniently, and the legacy `None`-to-`''` normalisation where DTM-11 states it.                                                                                                                                                                                                                                         |
| CL-07 | An app imports **its own** request/response models from its client library — the library is the contract's single home, and both sides of every in-workspace call validate against one model class.                                                                                                                                                                                                                                                                           |

### Per-library contracts

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL-10 | `aurelius_atlas_server_client.models` states the admin shapes as models — `AtlasVersion` (`Version`/`Revision`/`Name`/`Description`), `AtlasStatus` (`Status`), `AtlasSessionInfo` (settings keys + `userName`/`groups`/`timezones`/`_csrfToken`), `AtlasErrorInfo` (`errorCode`/`errorMessage`/`errorCause`) — reusing `aurelius-atlas-model` for typedef bodies, which it never forks.                                                                                                                                                                                                                                                                                     |
| CL-11 | `AtlasClient` answers the server's implemented routes: `admin.version()`, `admin.status()`, `admin.session()`, `admin.readiness()`, `liveness()`; the typedef calls `typedef_by_name`, `typedef_by_guid`, `typedefs(filter)`, `typedef_headers(filter)`, the six kind lookups (`enumdef`…`businessmetadatadef`, by name and guid), and the `create`/`update`/`delete` writes — each path mirroring `routes/admin.py` / `routes/types.py`. `get_lineage(guid, depth, direction) -> LineageInfo` reads `v2/lineage/{guid}` (CL-12's model; the guid is a `UUID` — DV-78, DD-213) — the client side of the feed whose **server** route lands with 5.1; 8.2 is its first caller. |
| CL-12 | `aurelius_atlas_server_client.lineage` owns the `v2/lineage/{guid}` body — `LineageInfo`, `EntityHeaderLite`, `LineageRelation`, `Direction` — moved verbatim from 8.2's app module (LM-04's model, LM-01's `Direction`), the entity guids typed as `UUID` (`guidEntityMap` keys, headers, relation endpoints — DV-78; `relationshipId` stays `str`); the flattening (`flatten_relations`, `PROCESS_TYPES`, `LINEAGE_RULES`) is 8.2's app logic and stays in the app.                                                                                                                                                                                                        |
| CL-20 | `aurelius_atlas_data2model_client` owns the `/extract` contract: the rule-model family (`ExtractionRequest`, `RulesDef`, `ElementRule`, `RelationRule`, `ViewRule`, `ViewNodeRule`, `ViewEdgeRule`, `MappingEntry`, `LegacyStr`, the DTM-11 validation messages) moved out of the app, and the new `ExtractionResponse` (`metadata: list[MetadataEntry]`, `model: str` — the ar3 JSON string).                                                                                                                                                                                                                                                                               |
| CL-21 | `Data2ModelClient.extract(request)` posts an `ExtractionRequest` and returns an `ExtractionResponse`; the rules document the 8.2 chain sends is built from the lib's rule models, so the caller's payload validates as the server's body.                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| CL-30 | `aurelius_atlas_lineage_model_client` states `GET /` (8.2): `LineageModelParams` (`guid` — a `UUID`, DV-78 — `depth` ≥ 1 default 3, `direction`, the LM-01 shape) and `LineageModelResponse` (the `{model, metadata}` passthrough of `/extract`, LM-04); `LineageModelClient.get(guid, depth, direction)` maps a 204 to `None` (LM-05/LM-06's empty answer).                                                                                                                                                                                                                                                                                                                 |
| CL-40 | `aurelius_atlas_validate_entity_client` states `POST /` (8.3): `ValidationResponse` — the four governance cards (`dataEntity`/`definition`/`domainLead`/`name`, each `items` + `isNonCompliant`) as the browser's `GovQualityApi` consumes them (VE-02); `validate(entity)` posts any mapping — the body is not a model, because the mock never reads it (VE-01, DD-201).                                                                                                                                                                                                                                                                                                    |

### Wiring rules

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL-50 | Each app's `create_app` keeps its injectable seams; the upstream clients of 8.2 inject there (the `http=` seam becomes typed clients, DD-200). A client library's models cross the app boundary: the app validates its **request** body with the library's model, the library's client parses the **response** into the library's model, and the app's response bytes stay verbatim (no `response_model` filtering — 8.1's scenarios compare whole bodies; the response model states the contract the server's own tests assert against). |

## Aurelius origin

The reference is the Aurelius source (ADR 055 R4) and this workspace's own routes:

- `libs/atlas/api` (`TypeDefsService`, `AdminService`, DTOs) — the Angular client
  this is the Python twin of; the DTO names and endpoint paths match it.
- `backend/m4i-data2model` (`extract` endpoint: `{metadata, model}`),
  `backend/m4i-lineage-model` (`lineage_model.py`: the rules dict, the fetch/extract
  chain), `backend/m4i-validate-entity` (`mock_response`, the `output` dict).
- `libs/m4i-atlas-core`'s `LineageInfo` (the camelCase wire shape now owned here).
- This workspace: `apps/aurelius-atlas-server/aurelius_atlas_server/routes/{admin,types}.py`
  and `errors.py` (the admin/types paths and the `{errorCode, errorMessage}` body the
  client mirrors), and the 8.1–8.3 specs for the aux-API contracts.

## Deviations

None of Atlas (ADR 052 — the wire contracts are unchanged; 8.1–8.3's DVs stand).
Deliberate workspace decisions, recorded as DD-203 (the contract's home),
DD-204 (async client, no env — superseded on construction by DD-205) and
DD-205 (the `httpx.AsyncClient` is provided externally) in the design log — this
increment adds no `DV-` rows because it changes no wire behaviour.

## Data contracts

- `aurelius_atlas_server_client`: `AtlasClient(http, token)` (`http` an externally built `httpx.AsyncClient`),
  `.admin` (`version() -> AtlasVersion`, `status() -> AtlasStatus`, `session() -> AtlasSessionInfo`,
  `readiness() -> str`, `liveness() -> str`), `.types` (`typedef_by_name(name) -> AtlasBaseTypeDef`,
  `typedef_by_guid(guid)`, `typedefs(params) -> AtlasTypesDef`, `typedef_headers(params) -> list[AtlasTypeDefHeader]`,
  `enumdef_by_name(name) -> AtlasEnumDef` … `businessmetadatadef_by_guid(guid)`,
  `create_typedefs(AtlasTypesDef) -> AtlasTypesDef`, `update_typedefs(...)`, `delete_typedefs(...) -> None`,
  `delete_typedef_by_name(name) -> None`), `lineage.LineageInfo` (+`EntityHeaderLite`, `LineageRelation`, `Direction`),
  `models.AtlasErrorInfo`, `AtlasClientError`.
- `aurelius_atlas_data2model_client`: the rule-model family (CL-20) at the package root,
  `ExtractionResponse`, `Data2ModelClient(http, token).extract(request) -> ExtractionResponse`,
  `Data2ModelClientError`.
- `aurelius_atlas_lineage_model_client`: `LineageModelParams`, `LineageModelResponse`,
  `LineageModelClient(http, token).get(guid: UUID, depth=3, direction="BOTH") -> LineageModelResponse | None`,
  `LineageModelClientError`.
- `aurelius_atlas_validate_entity_client`: `ValidationResponse` (+card/item models),
  `ValidateEntityClient(http, token).validate(entity: Mapping) -> ValidationResponse`,
  `ValidateEntityClientError`.
- Apps: `aurelius_atlas_data2model.rules` re-exports its family from the client lib (a
  thin compatibility module, so the app's docstrings keep citing DTM rules); `aurelius_atlas_lineage_model.lineage`
  keeps `PROCESS_TYPES`, `LINEAGE_RULES`, `flatten_relations`, `UpstreamError` and imports the
  models from `aurelius_atlas_server_client.lineage`; `create_app(settings, auth=None, atlas=None, d2m=None)`.

## Acceptance

- Unit (per lib, every public function named by `covers` with a CL id; basenames
  unique across the workspace, the pytest convention):
  `libs/python/aurelius-atlas-server-client/tests/test__aurelius_atlas_server_client_models.py`
  (CL-10), `test__aurelius_atlas_server_client_lineage.py` (CL-12),
  `test__aurelius_atlas_server_client_client.py` (CL-01..05, CL-11),
  `libs/python/aurelius-atlas-data2model-client/tests/test__aurelius_atlas_data2model_client_models.py`
  (CL-20), `test__aurelius_atlas_data2model_client_client.py` (CL-01..04, CL-21),
  `libs/python/aurelius-atlas-lineage-model-client/tests/test__aurelius_atlas_lineage_model_client_models.py`
  (CL-30), `test__aurelius_atlas_lineage_model_client_client.py`,
  `libs/python/aurelius-atlas-validate-entity-client/tests/test__aurelius_atlas_validate_entity_client_models.py`
  (CL-40), `test__aurelius_atlas_validate_entity_client_client.py`;
  CL-06/CL-07/CL-50 are enforced by the apps' suites (importing the
  lib's models) and the client suites' transport fakes.
- The apps' suites stay green unchanged in behaviour: the 8.1/8.2/8.3 unit suites
  prove no wire change. The e2e suites (`nx e2e aurelius-atlas-{data2model,lineage-model,validate-entity,server}`)
  drive the containers **through the client libraries** — each conftest's `api`
  fixture wraps a CA-verified `httpx.AsyncClient` in the app's client (CL-21, CL-30,
  CL-40, CL-11), so the libraries are proven against the real apps, not only a fake
  transport. The raw-httpx fixtures stay where the library has no route: the parity
  scenarios (`run_scenario` takes `httpx.AsyncClient`), the auth-gate 401s, liveness,
  and the malformed-body call of VE-01.
- `uv run aurelius-atlas-trace check` names every public function (CL ids resolve).
- Parity: none added — no wire behaviour changes; the existing server scenarios
  (`scenarios/*.scenario.yaml`) and 8.1–8.3 scenarios are the guard.

Run: `uv run pytest libs/python/aurelius-atlas-{server,data2model,lineage,validate-entity}*-client*`
and the app suites; CI gate `nx affected -t test e2e -c ci`.

# 8.23 Aux API OpenAPI contracts

- **Status:** in progress
- **Pull request:** –
- **Records:** adds AUX-06 and AUX-07 (the increment's shared rule table is with
  [`aurelius-atlas-data2model`][part-0]) and DD-557..559 ([design][design]). Relies on 8.0's
  foundation (AUX-01..05), on this app's surface rules (LM-05..08), and on the server's OpenAPI
  shape (PR #337: `openapi.py`, the development-only spec surface).

This page is the `aurelius-atlas-lineage-model` part of increment 8.23; its rule table is the
increment's shared set. The other parts are with [`aurelius-atlas-data2model`][part-0],
[`aurelius-atlas-validate-entity`][part-1], and [`aurelius-atlas-embedder`][part-2].

[part-0]: ../../../aurelius-atlas-data2model/specs/8-23-aux-api-openapi-contracts/spec.md
[part-1]: ../../../aurelius-atlas-validate-entity/specs/8-23-aux-api-openapi-contracts/spec.md
[part-2]: ../../../aurelius-atlas-embedder/specs/8-23-aux-api-openapi-contracts/spec.md
[design]: ../../../aurelius-atlas-data2model/specs/8-23-aux-api-openapi-contracts/design.md

## Scope

The server names every REST body and answer with a model in its OpenAPI document, and answers the
document and the Swagger UI under development only (PR #337). This app answers with hand-built
verbatim bytes (CL-20), so FastAPI cannot infer an answer from a handler, and its route documents
FastAPI's own 422 validation body, which the app never answers. This increment gives the app the
server's posture.

Delivered here (`aurelius-atlas-lineage-model`):

- `GET /` names its answer in the document: the 200 is the client library's `ExtractionResponse`
  (CL-20), and the 204 stays empty (LM-05, LM-06). The route declares the answer with
  `response_model`, which documents the shape and leaves the bytes verbatim, because the route
  returns a `Response` (DD-559). The body's shape comes from the route's own query parsing, so
  `guid` keeps its UUID rule and `depth` its minimum (LM-07).
- The document states the failure the app answers: the automatic 422 becomes the `400` with the
  Atlas error body of the root's handler (LM-07, DV-72's posture).
- The settings gain `environment` (default `production`); the app serves `/openapi.json` and
  `/docs` under development only (AUX-07, DD-557). The dev `.env` turns it on.
- `tests/test__aurelius_atlas_lineage_model_openapi.py` fails when an answer lacks its model,
  when a JSON answer says nothing, or when a `$ref` names a schema the document never carries.

Explicitly not delivered, with the reason:

| Not delivered                              | Why                                                      |
| ------------------------------------------ | -------------------------------------------------------- |
| The upstream clients change                | CL-20's models already carry the shapes                  |
| The contract answers in production         | AUX-07 keeps the surface development-only, as the server |
| Each answer moves to FastAPI serialization | CL-20's scenarios compare whole bodies; the bytes stay   |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The two rules
govern every auxiliary API, so the four spec pages of this increment each restate the same two
rows. 8.0's AUX-01..05 stay unchanged.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AUX-06 | Every JSON body and every JSON answer of an auxiliary API is named by a model in the app's OpenAPI document: a `$ref` to a component schema, or a schema with properties or a key/value shape. Each failure response states the status and the body the app actually answers, so FastAPI's automatic 422 validation body appears only where the app answers it (the embedder, in OpenAI's error shape). A route without a declared shape, a `$ref` to a schema the document does not carry, or a bare-object answer fails that app's guard test. |
| AUX-07 | An auxiliary API answers `/openapi.json` and the Swagger UI (`/docs`) only when its `ENVIRONMENT` setting is `development`; the default is `production`, where both answer 404. ReDoc is never served. The server answers its own surface under the same condition.                                                                                                                                                                                                                                                                              |

## Aurelius origin

- The server's OpenAPI shape (PR #337): `aurelius_atlas_server/openapi.py` declares what the
  hand-parsed routes read, and the spec surface is gated on the environment. This increment is the
  same posture for the auxiliary APIs, ported to apps that answer through a `Response`.
- `backend/m4i-lineage-model` (Flask, no document): the legacy ships no machine-readable contract,
  so there is no shape to copy; the models are Aurelius' own (CL-20).

## Deviations

None new. The rules formalise what 8.2 already built: the shapes enter the document from the
models the app already answers with.

## Acceptance

Run offline: `uv run pytest apps/aurelius-atlas-lineage-model/tests`, or
`nx test aurelius-atlas-lineage-model -c ci`.

- AUX-06: `test__every_answer_declares_its_model` (no bare answer, no dangling `$ref`, so no
  automatic 422 left standing) and `test__the_lineage_answer_names_the_client_model`
  (`tests/test__aurelius_atlas_lineage_model_openapi.py`).
- AUX-07: the production assertion inside `test__the_app_is_built_from_the_settings` and
  `test__the_development_environment_serves_the_openapi_surface`
  (`tests/test__aurelius_atlas_lineage_model_app.py`).
- The verbatim answer posture (CL-20) stays proven by the existing route and e2e scenario suites,
  unchanged.

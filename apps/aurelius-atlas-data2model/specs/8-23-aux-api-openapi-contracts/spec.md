# 8.23 Aux API OpenAPI contracts

- **Status:** in progress
- **Pull request:** –
- **Records:** adds AUX-06 and AUX-07 (this page holds the increment's shared rule table) and
  DD-557..559 ([design](design.md)). Relies on 8.0's foundation (AUX-01..05), on each app's own
  surface rules (DTM-10, LM-08, VE-03, EMB-01..07), and on the server's OpenAPI shape (PR #337:
  `openapi.py`, the development-only spec surface).

This page is the `aurelius-atlas-data2model` part of increment 8.23; its rule table is the
increment's shared set. The other parts are with [`aurelius-atlas-lineage-model`][part-0],
[`aurelius-atlas-validate-entity`][part-1], and [`aurelius-atlas-embedder`][part-2].

[part-0]: ../../../aurelius-atlas-lineage-model/specs/8-23-aux-api-openapi-contracts/spec.md
[part-1]: ../../../aurelius-atlas-validate-entity/specs/8-23-aux-api-openapi-contracts/spec.md
[part-2]: ../../../aurelius-atlas-embedder/specs/8-23-aux-api-openapi-contracts/spec.md

## Scope

The server names every REST body and answer with a model in its OpenAPI document, and answers the
document and the Swagger UI under development only (PR #337). The four auxiliary FastAPI APIs have
no such contract. data2model, lineage-model, and validate-entity answer with hand-built verbatim
bytes (CL-50), so FastAPI cannot infer an answer from a handler, and every route documents FastAPI's
own 422 validation body, which none of these apps answers. This increment gives each app the
server's posture. The three scanners are out of scope: they are CronJob CLIs, not APIs.

Delivered here (`aurelius-atlas-data2model`):

- `POST /extract` names its body and its answer in the document. The body is the client library's
  `ExtractionRequest`, which the route's signature already parses; the answer is its
  `ExtractionResponse` (CL-20). The route declares the answer with `response_model`, which
  documents the shape and leaves the bytes verbatim, because the route returns a `Response`
  (CL-50, DD-559).
- The document states the validation failure the app answers: the automatic 422 becomes the `400`
  with the Atlas error body of the root's `RequestValidationError` handler (DTM-04, DV-79).
- The settings gain `environment` (default `production`); the app serves `/openapi.json` and
  `/docs` under development only (AUX-07, DD-557). The dev `.env` turns it on.
- `tests/test__aurelius_atlas_data2model_openapi.py` fails when a route lacks its body or answer,
  when a JSON answer says nothing, or when a `$ref` names a schema the document never carries.

Explicitly not delivered, with the reason:

| Not delivered                                  | Why                                                      |
| ---------------------------------------------- | -------------------------------------------------------- |
| The three scanners get a document              | CronJob CLIs, not HTTP APIs                              |
| The client libraries change                    | CL-20's models already carry the shapes                  |
| The contract answers in production             | AUX-07 keeps the surface development-only, as the server |
| Each aux answer moves to FastAPI serialization | CL-50 compares whole bodies; the bytes stay verbatim     |

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
- `backend/m4i-data2model` (Flask, no document): the legacy ships no machine-readable contract, so
  there is no shape to copy; the models are Aurelius' own (CL-20).

## Deviations

None new. The rules formalise what 8.1 already built: the shapes enter the document from the
models the app already parses and answers with.

## Acceptance

Run offline: `uv run pytest apps/aurelius-atlas-data2model/tests`, or
`nx test aurelius-atlas-data2model -c ci`.

- AUX-06: `test__every_route_declares_its_body_and_answer` (no bare answer, no dangling `$ref`,
  no write without a body, so no automatic 422 left standing) and
  `test__the_extract_answer_names_the_client_model`
  (`tests/test__aurelius_atlas_data2model_openapi.py`).
- AUX-07: `test__the_app_publishes_no_openapi_docs_or_redoc` (production) and
  `test__the_development_environment_serves_the_openapi_surface`
  (`tests/test__aurelius_atlas_data2model_app.py`).
- The verbatim answer posture (CL-50) stays proven by the existing route and e2e scenario suites,
  unchanged.

# 8.23 Aux API OpenAPI contracts

- **Status:** in progress
- **Pull request:** –
- **Records:** adds AUX-06 and AUX-07 (the increment's shared rule table is with
  [`aurelius-atlas-data2model`][part-0]) and DD-557..559 ([design][design]). Relies on 8.0's
  foundation (AUX-01..05), on this app's surface rules (EMB-01..07), and on the server's OpenAPI
  shape (PR #337: `openapi.py`, the development-only spec surface).

This page is the `aurelius-atlas-embedder` part of increment 8.23; its rule table is the
increment's shared set. The other parts are with [`aurelius-atlas-data2model`][part-0],
[`aurelius-atlas-lineage-model`][part-1], and [`aurelius-atlas-validate-entity`][part-2].

[part-0]: ../../../aurelius-atlas-data2model/specs/8-23-aux-api-openapi-contracts/spec.md
[part-1]: ../../../aurelius-atlas-lineage-model/specs/8-23-aux-api-openapi-contracts/spec.md
[part-2]: ../../../aurelius-atlas-validate-entity/specs/8-23-aux-api-openapi-contracts/spec.md
[design]: ../../../aurelius-atlas-data2model/specs/8-23-aux-api-openapi-contracts/design.md

## Scope

The server names every REST body and answer with a model in its OpenAPI document, and answers the
document and the Swagger UI under development only (PR #337). The embedder's two routes already
take and answer pydantic models, so FastAPI infers their shapes; the gap is the document's failure
contract (it promises FastAPI's own 422 body, where the app answers in OpenAI's error shape,
EMB-05) and the development-only posture of the surface. This increment closes both.

Delivered here (`aurelius-atlas-embedder`):

- `POST /v1/embeddings` and `GET /v1/models` keep their inferred shapes, and each refusal names
  the OpenAI error body: the 404 and the 503 carry it (EMB-05, EMB-07), and the automatic 422
  now carries it too (DD-559). FastAPI's `HTTPValidationError` and `ValidationError` schemas,
  which no route answers, leave the document; the app's `ErrorResponse` model enters it.
- The settings gain `environment` (default `production`); the app serves `/openapi.json` and
  `/docs` under development only (AUX-07, DD-557). The app ships no `.env`, so the project's
  serve command carries `AURELIUS_ATLAS_EMBEDDER_ENVIRONMENT=development`.
- `tests/test__aurelius_atlas_embedder_openapi.py` fails when a route lacks its body or answer,
  when a JSON answer says nothing, or when a `$ref` names a schema the document never carries.

Explicitly not delivered, with the reason:

| Not delivered                      | Why                                                      |
| ---------------------------------- | -------------------------------------------------------- |
| A bearer gate on the surface       | DD-432: the embedder checks no tokens, by design         |
| The contract answers in production | AUX-07 keeps the surface development-only, as the server |
| An `.env` file for the app         | the serve command sets the one dev value (DD-557)        |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The two rules
govern every auxiliary API, so the four spec pages of this increment each restate the same two
rows. 8.0's AUX-01..05 stay unchanged.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AUX-06 | Every JSON body and every JSON answer of an auxiliary API is named by a model in the app's OpenAPI document: a `$ref` to a component schema, or a schema with properties or a key/value shape. Each failure response states the status and the body the app actually answers, so FastAPI's automatic 422 validation body appears only where the app answers it (the embedder, in OpenAI's error shape). A route without a declared shape, a `$ref` to a schema the document does not carry, or a bare-object answer fails that app's guard test. |
| AUX-07 | An auxiliary API answers `/openapi.json` and the Swagger UI (`/docs`) only when its `ENVIRONMENT` setting is `development`; the default is `production`, where both answer 404. ReDoc is never served. The server answers its own surface under the same condition.                                                                                                                                                                                                                                                                              |

EMB-05's posture is what AUX-06 states here: a validation failure is the app's own 422, answered
in OpenAI's error shape (`ErrorResponse`, the `error` object with `message`, `type`, `param`,
`code`). The shape rule (the `model` must match, `input` is a string or list of strings) already
lives in the route's `EmbeddingRequest` model and needs no change.

## Aurelius origin

- The server's OpenAPI shape (PR #337): `aurelius_atlas_server/openapi.py` declares what the
  hand-parsed routes read, and the spec surface is gated on the environment. This increment is the
  same posture for the auxiliary APIs, ported to the app that already speaks in models.
- The OpenAI `POST /v1/embeddings` contract (EMB-01, EMB-05): the document names the OpenAI
  request and response models the app copies, so a generic OpenAI client reads the app's surface.

## Deviations

None new. The rules formalise what 11.2 already built: the same OpenAI shapes, now with a
document whose failures state the truth.

## Acceptance

Run offline: `uv run pytest apps/aurelius-atlas-embedder/tests`, or
`nx test aurelius-atlas-embedder -c ci`.

- AUX-06: `test__every_route_declares_its_body_and_answer` and
  `test__the_validation_failure_names_the_openai_error`
  (`tests/test__aurelius_atlas_embedder_openapi.py`).
- AUX-07: `test__the_openapi_surface_answers_only_under_development`
  (`tests/test__aurelius_atlas_embedder_app.py`).
- The OpenAI response posture (EMB-01/06) stays proven by the existing route tests and the e2e
  suite over TLS, unchanged.

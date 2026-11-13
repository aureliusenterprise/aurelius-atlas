# 8.23 Aux API OpenAPI contracts

- **Status:** in progress
- **Pull request:** –
- **Records:** adds AUX-06 and AUX-07 (the increment's shared rule table is with
  [`aurelius-atlas-data2model`][part-0]) and DD-557..559 ([design][design]). Relies on 8.0's
  foundation (AUX-01..05), on this app's surface rules (VE-01..04, VEV-01/02), and on the server's
  OpenAPI shape (PR #337: `openapi.py`, the development-only spec surface).

This page is the `aurelius-atlas-validate-entity` part of increment 8.23; its rule table is the
increment's shared set. The other parts are with [`aurelius-atlas-data2model`][part-0],
[`aurelius-atlas-lineage-model`][part-1], and [`aurelius-atlas-embedder`][part-2].

[part-0]: ../../../aurelius-atlas-data2model/specs/8-23-aux-api-openapi-contracts/spec.md
[part-1]: ../../../aurelius-atlas-lineage-model/specs/8-23-aux-api-openapi-contracts/spec.md
[part-2]: ../../../aurelius-atlas-embedder/specs/8-23-aux-api-openapi-contracts/spec.md
[design]: ../../../aurelius-atlas-data2model/specs/8-23-aux-api-openapi-contracts/design.md

## Scope

The server names every REST body and answer with a model in its OpenAPI document, and answers the
document and the Swagger UI under development only (PR #337). This app reads its body as a raw
value and checks the shape in the handler, so the document said nothing about the draft, and its
route documented FastAPI's own 422 validation body, which the app never answers. This increment
gives the app the server's posture.

Delivered here (`aurelius-atlas-validate-entity`):

- `POST /` names its body and its answer in the document. The body parses as the app-side
  `DraftEntity` model (DD-558): `attributes` is a required JSON object and the rest of the draft is
  ignored (VEV-01). The handler's `isinstance` check and its `DraftRejectedError` handler leave the
  app, because the model now refuses what the handler refused; the 400 answer and its message
  prefix stay as VEV-01 states them. The answer is the client library's `ValidationResponse`
  (CL-40, VEV-02).
- The document states the failure the app answers: the automatic 422 becomes the `400` with the
  Atlas error body of the root's handler (VEV-01, DV-79's posture).
- The settings gain `environment` (default `production`); the app serves `/openapi.json` and
  `/docs` under development only (AUX-07, DD-557). The dev `.env` turns it on.
- `tests/test__aurelius_atlas_validate_entity_openapi.py` fails when a route lacks its body or
  answer, when a JSON answer says nothing, or when a `$ref` names a schema the document never
  carries.

Explicitly not delivered, with the reason:

| Not delivered                            | Why                                                          |
| ---------------------------------------- | ------------------------------------------------------------ |
| The client library's loose draft mapping | CL-40's leniency is the caller's; the document names the app |
| The contract answers in production       | AUX-07 keeps the surface development-only, as the server     |
| The verdicts' shape changes              | 12.7 owns it; only its declaration moved here                |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The two rules
govern every auxiliary API, so the four spec pages of this increment each restate the same two
rows. 8.0's AUX-01..05 stay unchanged.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AUX-06 | Every JSON body and every JSON answer of an auxiliary API is named by a model in the app's OpenAPI document: a `$ref` to a component schema, or a schema with properties or a key/value shape. Each failure response states the status and the body the app actually answers, so FastAPI's automatic 422 validation body appears only where the app answers it (the embedder, in OpenAI's error shape). A route without a declared shape, a `$ref` to a schema the document does not carry, or a bare-object answer fails that app's guard test. |
| AUX-07 | An auxiliary API answers `/openapi.json` and the Swagger UI (`/docs`) only when its `ENVIRONMENT` setting is `development`; the default is `production`, where both answer 404. ReDoc is never served. The server answers its own surface under the same condition.                                                                                                                                                                                                                                                                              |

VE-01 of 8.3 (the mock) and VEV-01 of 12.7 stay unchanged in behaviour: the same draft, the same
400, the same message prefix. The rule gains its enforcement at the boundary instead of the
handler.

## Aurelius origin

- The server's OpenAPI shape (PR #337): `aurelius_atlas_server/openapi.py` declares what the
  hand-parsed routes read, and the spec surface is gated on the environment. This increment is the
  same posture for the auxiliary APIs, ported to the app that reads a raw body.
- `backend/m4i-validate-entity` (Flask, no document): the legacy ships no machine-readable
  contract, so there is no shape to copy; the models are Aurelius' own (CL-40).

## Deviations

None new. The rules formalise what 12.7 already built: the same parse, the same 400, now named by
a model the document carries.

## Acceptance

Run offline: `uv run pytest apps/aurelius-atlas-validate-entity/tests`, or
`nx test aurelius-atlas-validate-entity -c ci`.

- AUX-06: `test__every_route_declares_its_body_and_answer` (no bare answer, no dangling `$ref`,
  so no automatic 422 left standing) and `test__the_body_and_answer_name_their_models`
  (`tests/test__aurelius_atlas_validate_entity_openapi.py`).
- AUX-07: the production assertion inside `test__the_app_is_built_from_the_settings` and
  `test__the_development_environment_serves_the_openapi_surface`
  (`tests/test__aurelius_atlas_validate_entity_app.py`).
- The 400 posture (VEV-01) stays proven by the existing parametrized route tests, unchanged.

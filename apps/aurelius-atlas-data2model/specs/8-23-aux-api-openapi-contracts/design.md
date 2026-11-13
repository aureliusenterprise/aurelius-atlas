# 8.23 Design decisions

The technical decisions of increment 8.23, written next to its
[spec](spec.md) per [ADR 051](../../../../docs/architecture/adr/051-the-conversion-proceeds-in-specified-increments.md).
The increment's four spec pages share one rule table; this file is the single home of its entries.

## DD-557. The auxiliary APIs serve their OpenAPI surface under development only

- **Status:** Proposed
- **Increment:** 8.23
- **Date:** 2026-11-13

**Decision.** Each auxiliary API gains an `ENVIRONMENT` setting with the values `production`
(the default) and `development`. The app builds FastAPI with `openapi_url="/openapi.json"` and
`docs_url="/docs"` only under development, and with both `None` otherwise. ReDoc stays `None` in
both. The dev `.env` of each app sets the value, and the embedder's serve command carries it as a
prefix because the app ships no `.env`.

**Reason.** AUX-07. A production deployment of an auxiliary API answers its whole surface shape
to any caller, which the server refused to do (PR #337). One setting per app, read like every
other setting, keeps the contract close during development and shut in production.

**Alternatives.** Serving the surface always: the posture the server abandoned. A separate port or
hostname for the contract: more wiring for one setting's job. Gating on a flag outside the settings
class: the server's shape puts every knob in settings, read once at start-up (SRV-01's pattern).

## DD-558. validate-entity parses the draft body as an app-side model

- **Status:** Proposed
- **Increment:** 8.23
- **Date:** 2026-11-13

**Decision.** `POST /` of validate-entity takes an app-side `DraftEntity` model instead of a raw
`dict`: `attributes` is a required JSON object, and the model ignores the rest of the body
(VEV-01). The manual `isinstance` guard and its `DraftRejectedError` handler are deleted; the
route's existing `RequestValidationError` handler answers a bad body with the same `400` Atlas
error body and the same message prefix `invalid validation request:`.

**Reason.** AUX-06 needs the body named by a model in the document, and the parse at the boundary
is what names it. The client library's loose mapping (CL-40) stays as it is, because the document
speaks for the app, not for the caller's leniency.

**Alternatives.** Declaring a schema while the route keeps reading a raw dict: the document then
states a shape no code enforces, the failure PR #337 closed on the server. Reusing the client
library's model: it accepts a missing `attributes`, which VEV-01 refuses.

## DD-559. A `response_model` documents a hand-built answer, and each app corrects the automatic 422

- **Status:** Proposed
- **Increment:** 8.23
- **Date:** 2026-11-13

**Decision.** The aux routes that answer through a `Response` built from a client model
(data2model, lineage-model, validate-entity) keep the hand-built bytes and declare the answer with
`response_model`, which FastAPI uses for the document only. Each app's `create_app` wraps
`app.openapi`: the three Atlas-shaped apps replace the automatic 422 response with the `400` and
Atlas error body their root handler answers, and the embedder replaces the automatic 422 schema
with its `ErrorResponse` model and drops the validation schemas no route answers.

**Reason.** AUX-06. FastAPI cannot infer the answer of a route that returns a `Response`, and its
generated document promises a 422 body that no aux app ever answers (DV-79, EMB-05). A
`response_model` on such a route is document-only at runtime, so CL-50's verbatim bytes are
untouched, and the small `openapi` wrapper makes the document say what the app does.

**Alternatives.** Return the model and let FastAPI serialize it: it rewrites body bytes the
parity scenarios compare (CL-50). Hand-writing whole schemas in a registry like the server's
`openapi.py`: these routes already hold the models in their parse and their `Response`, so the
registry would restate them. Leaving the automatic 422 in the document: a contract that lies to
the caller about a status the app never sends.

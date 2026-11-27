# 21.1 Design decisions

## DD-887 — FastMCP speaks HTTP only, on its own port

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-01, MCP-16, ADR 072, ADR 045, DD-197

The MCP boundary is protocol machinery we have no reason to own: framing, session
negotiation, schema derivation from Python signatures, transport. FastMCP is the convention
to borrow (ADR 045), and its dependency is confined to this one app so the slice stays
removable (ADR 002).

The app runs only the Streamable HTTP transport through FastMCP's ASGI app
(`mcp.http_app()`), served by uvicorn exactly as the other auxiliary APIs serve theirs.
stdio is not offered: an MCP stdio server is a local process an MCP client spawns, which
suits a developer's laptop tool, not a shared governance service whose access is decided in
one place (ADR 013, ADR 038). A local user who wants stdio runs the same image and reaches
the same endpoint; there is nothing a stdio process would see that the HTTP one does not.

The app is an MCP server, not a REST API, so it answers no OpenAPI document or docs page
(AUX-07's surface is meaningless without routes). It exposes exactly one extra HTTP route,
`GET /liveness`, for the container healthcheck (MCP-15). The port joins the aux band as
21005, after the embedder's 21004.

Settings keep the per-project prefix rule (root `AGENTS.md`): `AURELIUS_ATLAS_MCP_`,
pydantic-settings, read once at start-up (DD-197).

## DD-888 — One verifier: the gate is Starlette middleware over the shared library

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-02, MCP-15, AUX-02..AUX-05, DD-197, ADR 013

FastMCP ships its own JWT verification (`JWTVerifier`) that takes a JWKS URI, issuer and
audience. Using it would put a second token verifier in the workspace, next to
`aurelius-atlas-auth`, and the two would drift: the shared library's audience rule is the
union of the `azp` and `aud` claims (AUX-04), which pyjwt's plain audience check does not
express, and its JWKS reads ride a circuit breaker (AUX-02). Two verifiers, one product, is
exactly the drift ADR 017 exists to prevent.

So the gate is a thin Starlette middleware in front of the FastMCP ASGI app: it reads the
`Authorization` header, calls `KeycloakAuth.verify` (the same code the 8.x apps gate
routes with), and on failure answers `401` with `WWW-Authenticate` without ever opening an
MCP session. The verified claims are handed downstream through the ASGI scope's `state`,
and the middleware records the acting user for the tool layer (DD-890).

`/liveness` bypasses the middleware, which also matches FastMCP's own rule that custom
routes sit outside the auth gate. The middleware is deliberately a path allow-list rather
than a deny-list: a future route is unauthenticated until someone names it, which is the
safe default.

## DD-889 — Tools carry the surface; reads answer headers, not entities

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-04..MCP-13, R2 (ADR 072)

MCP has three component kinds — tools, resources, prompts. This surface uses only tools.
Resources are readable documents at a URI, and every catalogue read here needs parameters
(a query, a type, pagination) or an authority check on the caller, so they would be tools
with a worse schema. Prompts are canned message templates owned by the caller's own
domain, not ours. Adding the kinds "because MCP has them" would be a contract we owe
forever (ADR 072's consequence).

Twelve tools, named in the spec (MCP-04), is the deliberate budget. Every one maps to a
method the client library already answers, so none adds server behaviour (R4).

Reads answer **compact shapes**: `search_entities` returns headers (guid, display name,
type, classifications, qualified name, status), never whole entities, and glossary and
type reads return headers too (MCP-05, MCP-08, MCP-09). An LLM context window is the
scarce resource, and a basic search of a populated catalogue over full entities is
megabytes of JSON a model cannot read. The caller gets the guid and calls `get_entity`
for the one record it cares about (MCP-06). The header projection is written here and
drops the server's own bulk-header noise (`parameters`, `contacts`), which is a display
concern of the webapp (DV-208's shape).

## DD-890 — The caller's token rides a request-scoped context variable

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-03, MCP-06, CL-01, DD-205, DV-208

The app holds one `AtlasClient` and one `ValidateEntityClient`, built at start-up over one
shared httpx pool (DD-205). Neither carries a token, because no token belongs to the app.

Each MCP request gets the caller's token from the middleware (DD-888) and stores it in a
`ContextVar` for the duration of the call; the tool layer asks the client for a
`with_token(...)` wrapper (CL-01's design) built on a closure over that variable, so a
client created at start-up answers every caller without holding a credential (MCP-03). A
`ContextVar` is request-scoped across concurrent asyncio tasks — the failure mode of a
plain module-level token would be one agent's write running as another agent's user, which
MCP-03 forbids; the test set asserts the isolation.

A tool that runs with no token in scope (a bug, or a future stdio-style call path) fails
closed with the tool error of MCP-02, never anonymously.

## DD-891 — The write gate is the same claims rule, reached a second way

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-11, AUZ, DD-197, ADR 038

`aurelius-atlas-auth` gates FastAPI routes with `require_write`, which pulls the caller's
claims out of the FastAPI security scheme. There is no FastAPI request inside a FastMCP
tool, so the dependency cannot be reused as-is. The alternative — asking FastMCP for the
role from the already-verified claims — is what happens here: the middleware stows the
claims (DD-888), and the write tools consult a predicate that reads the same two claim
locations the library reads (`realm_access.roles` and
`resource_access.<audience>.roles`), against the same configured role.

The role names and the "empty role disables the gate, development only" rule are
`aurelius-atlas-auth`'s, not redefined here (ADR 017). The consequence is a second call
site for one rule; the test set pins the shape of both accepted locations so a future
change in the library's rule fails a test in this app too. A refusal is an MCP tool error
before any upstream request (MCP-11): the server never sees an unauthorised write.

## DD-892 — Proof is unit-level against a mock transport; the chain waits for deployment

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-14, ADR 056, ADR 012, DD-203, DD-223

This increment ships no parity scenarios and no e2e suite, and that is a stated gap, not
an omission:

- **No parity scenarios.** Parity (ADR 052) compares a ported behaviour against Apache
  Atlas 2.4.0 source. Atlas has no MCP server, so there is no reference to read a scenario
  from. The catalogue behaviour behind each tool is already pinned by the server and client
  increments; the tools add no behaviour to compare. DV-208 records the framework, not a
  behaviour difference.
- **No e2e.** A real-chain suite needs the realm client, the compose piece and the chart —
  the deployment increment (spec's Not delivered). Standing up a chain to prove what a
  mock transport already proves would repeat 8.x's pattern before its deployment landed.
- **Unit proof instead.** Tests run the real ASGI app over an in-memory transport: a fake
  issuer for the gate (the 8.0 library's test double, so MCP-02 proves the real verifier),
  and a `httpx.MockTransport` for the upstream (CL-02), so MCP-05..MCP-14 assert the exact
  request the server receives and the exact shape the tool answers. Every rule id is named
  (ADR 056).

MCP-14's failure text is asserted against a crafted upstream answer, because the whole
point is the mapping of a server error into a tool error without inventing an empty result.

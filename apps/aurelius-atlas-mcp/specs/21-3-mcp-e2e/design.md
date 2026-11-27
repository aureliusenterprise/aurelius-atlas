# 21.3 Design decisions

## DD-898 — The write role lives under the catalogue client, not the audience

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-11, MCP-28, MCP-30, DD-891, DD-208, AUZ-01, DD-300, DV-208

The chain found a live bug the unit suite could not see. `token_roles` reads the
caller's roles from `realm_access.roles` and `resource_access.<audience>.roles`,
where the audience is the app's own client (`aurelius` in every deployment). The
unit fakes mint exactly that shape, so 35 tests stayed green while the live
answer was wrong: a real Keycloak namespaces client roles per client, and
`atlas-write` is a role of the **catalogue** client `aurelius-atlas-server`
(`infra/keycloak/import/master.json`, the chart copy, and the server settings'
default `auth_client_id` all carry it). A browser token of the dev writer says
`resource_access["aurelius"].roles = ["aurelius-write"]` and
`resource_access["aurelius-atlas-server"].roles = [..., "atlas-write", ...]`.
Over the wire the old gate refused every write tool, even for a writer.

Three call sites read the same fact and agree on the answer: the server enforces
`atlas-write` from the catalogue client's entry (its own audience), the webapp's
`can-write-entities()` reads `hasResourceRole("atlas-write", atlasClientId)`
with `atlasClientId` defaulting to `aurelius-atlas-server`, and MCP now reads the
same client's entry. The app's audience stays `aurelius` — that is what the gate
verifies on the way in (MCP-02) — but the role lookup is configured separately,
as `AURELIUS_ATLAS_MCP_WRITE_ROLE_CLIENT` (default `aurelius-atlas-server`),
mirroring the webapp's runtime config rather than hard-wiring a second name.

DD-891 stands for the claim _locations_ (`realm_access` plus the one
`resource_access` entry); only the _which-client_ question changes, and it was
wrong there. The unit suite flips the fake it minted (the role under the
catalogue client now, and under the audience no longer) and the e2e suite proves
the real token's shape end to end (MCP-29, MCP-30).

## DD-899 — The chain is the aux layer stack at 21009, with no secret trail

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-25, MCP-26, DD-897, DD-200, DD-223, ADR 065, ADR 066, CIA-03

The stack copies the validate-entity chain's shape (the 12.7 pattern):
`e2e/compose.mcp.yaml` extends the project's stack piece and resets the proxy
network, so the e2e identity (host-mapped issuer, in-network legs, published
random port) layers over the same base the standalone stack includes — MCP-22's
keyless posture is inherited, not repeated. `e2e/docker-compose.yaml` names the
three services and their external networks, and states only the differences:
the server sidecar extends the server project's e2e base at the fixed
loopback-pinned port **21009** (DD-897's ladder: 21005..21008 are taken) with
`AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES: '["aurelius", "aurelius-atlas-validate-entity"]'` —
the browser's audience for everything the front door forwards, plus the verdicts
app's own client, which signs its rules leg (VEV-04, the same join the verdicts
suite's stack and the webapp's stack make); the verdicts sidecar extends
`compose.validate-entity.yaml`; the app joins the store network to reach both
by their certificate names.

The app publishes no fixed port (the suite asks compose for its mapping) and
names no secret or `OTEL_*` key anywhere in either file — the stack that would
first need a service identity is the one that proves it needs none (DV-208). The
suite leaves the shared `infra/*` stacks running and stops only its own three
containers (DD-223).

## DD-900 — The probe is a token probe: browser identity plus the write role

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-27, MCP-11, DD-200, DD-897, DV-75

The aux suites probe the app's own service leg before the stack starts, because
a stale realm import breaks the leg silently (DD-200's hint). MCP has no leg, so
its probe verifies the other identity: it mints the browser token (the public
`aurelius` client's password grant) and decodes it, and refuses to start the
stack unless the token carries the catalogue write role the write tools need
(MCP-11, MCP-28). A refusal or a role-less token raises the recreate-Keycloak
remedy with the reason — the running realm predates the grant — instead of
surfacing as twelve failing write assertions. It is the same fact the suite's
writer tests depend on, checked once before the work.

The reader half of the suite mints the realm's `aurelius-reader` the same way
(read role only). Both identities' passwords are required settings read from the
project's encrypted env, never defaults written into the test source, so the
refusal path (MCP-30) tests the gate rather than a missing credential.

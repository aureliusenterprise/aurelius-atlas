# aurelius-atlas-mcp

The MCP front door of the catalogue (increment 21.1, ADR 072): a FastMCP
service over Streamable HTTP that answers twelve catalogue tools. This file
covers wiring specific to this app; workspace-wide rules, including the
conversion workflow, live in the root `AGENTS.md`.

## Layout

The app is a protocol adapter, not an example-app: no `providers/` or
`routes/`, because FastMCP owns the routing and the tools are thin relays
(DD-889).

- `aurelius_atlas_mcp/app.py` — the composition root: `create_app(settings,
auth=None, clients=None)` builds the issuer verifier, the two upstream pools,
  the `FastMCP` server with its tool table and the anonymous `/liveness` custom
  route, and wraps it in `BearerGate`. `auth` and `clients` are injectable for
  tests.
- `aurelius_atlas_mcp/auth.py` — `BearerGate`: ASGI middleware in front of the
  FastMCP app (FastMCP cannot mount auth itself, DD-888). Missing/bad bearer →
  401 with `WWW-Authenticate: Bearer`; issuer down → 503; the liveness path is
  the allow-list. `token_roles`/`may_write` mirror the claim rule of
  `aurelius-atlas-auth` for the write gate (MCP-11).
- `aurelius_atlas_mcp/relay.py` — per-request plumbing: `bearer_token()` reads
  the token `BearerGate` stored in the ASGI state and fails closed;
  `AtlasClients` holds the two seeded clients; `relay()`/`upstream_tool_error()`
  map upstream errors to MCP tool errors that name the status (MCP-14).
- `aurelius_atlas_mcp/tools.py` — `register_tools(mcp, clients, audience,
write_role)`: the twelve tools (MCP-04..MCP-13). Each builds a
  per-request client through `clients.atlas.with_token(bearer_token)` so the
  caller's own token travels upstream (MCP-03, DD-890), and projects answers
  compactly (DD-889).
- `aurelius_atlas_mcp/settings.py` — `McpSettings`
  (`AURELIUS_ATLAS_MCP_` prefix; the auth block required, MCP-16). There is no
  service identity anywhere (DD-890).
- `aurelius_atlas_mcp/globals.py` — `NAME`, `LOGGER`, the ports/paths, the two
  upstream error texts.
- `aurelius_atlas_mcp/__main__.py` — the uvicorn entry point (port 21005, TLS
  when the cert pair is set).
- `tests/` — the unit suite (35 tests, offline): a fake RSA issuer,
  `FakeUpstream`/`call_tool` in `fake_upstream.py`, and a real MCP client
  session driven through an `ASGITransport` over the gated app (DD-892).

## Rules the app keeps

The MCP rules live in `apps/aurelius-atlas-mcp/specs/21-1-mcp-api/spec.md`
(with `design.md` beside it, DD-887..DD-892); tests cite them with
`@pytest.mark.covers(..., rules=["MCP-NN"])` (ADR 056). DV-208 records the one
deliberate difference from the 8.x aux APIs: this app forwards the caller's
token instead of its own service identity, because an agent session is a user
acting.

## Wiring Checklist

- `project.json` — `serve` depends on `decrypt`, `certgen` and dev Keycloak.
  `test`/`build`/`docker-*`/`decrypt`/`lint`/`typecheck` are inferred by
  `tools/plugins/python.ts` from `pyproject.toml`, `sourceRoot` and `tests/`.
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-mcp` after changing
  `.env`; CI regenerates plaintext `.env` from `.env.enc`).
- `tls.json` — the app's own certificate for `nx serve` (`nx certgen` runs
  through the tls plugin). The deployment increment adds the standalone compose
  piece, which needs the SANs of the compose service names.
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled),
  nonroot, liveness healthcheck that follows the cert pair.
- The caller gate is the shared lib (`aurelius-atlas-auth`): `BearerGate` wraps
  `KeycloakAuth.verify` around the FastMCP ASGI app. Audience `aurelius` in dev
  (the webapp's client, AUX-04): an agent's token is minted like the browser's.
- The write gate reads the caller's claims (`may_write` in `auth.py`) — role
  `atlas-write` in `realm_access.roles` or `resource_access.<audience>.roles`,
  the same claim shapes `aurelius-atlas-auth` accepts. A write tool must refuse
  before any upstream request (MCP-11).
- There is deliberately **no** service identity, OTLP ingest identity, client
  secret, or circuit breaker in this app (ADR 072, DV-208, DD-890). Do not add
  a mint here; upstreams see only the caller's bearer token.
- No `sonar-project.properties` yet: the SonarCloud project key comes with the
  deployment increment (the embedder shipped the same way first).
- `e2e/`, the Keycloak realm client, the Helm chart and `docker/compose.yaml`
  land in the deployment increment (the spec's "Not delivered" table, DD-892).

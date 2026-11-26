# aurelius-atlas-mcp

The MCP front door of the catalogue (increments 21.1–21.3, ADR 072): a FastMCP
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
- `aurelius_atlas_mcp/tools.py` — `register_tools(mcp, clients, role_client,
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
- `helm/` — the `atlas-mcp` chart (21.2, MCP-20): the aux chart shape without
  the credential join (DD-893). Conventions: `helm/AGENTS.md`; chart tests in
  the root `tests/test__charts_aux.py`.
- `docker/compose.yaml` — this project's piece of the standalone stack (ADR
  065, MCP-17): proxy service network, no published ports, folder-guarded
  `/certs` mount (`MCP_CERTS_DIR`). The webapp's `/mcp` location reaches it
  (DD-894).
- `specs/21-2-mcp-deployment/` — the deployment spec and design (MCP-17..24,
  DD-893..DD-897), beside the 21.1 pair.
- `e2e/compose.mcp.yaml` — the e2e layer over the stack piece (MCP-25): proxy
  network reset, the dev Keycloak issuer on the host, the two legs by their
  in-network certificate names. It names no secret and no `OTEL_*` key — the
  chain is the deployment's proof of DV-208's posture.
- `e2e/docker-compose.yaml` — the 21.3 chain: the server base at host port
  21009, the verdicts API layer, this app. Run through the `e2e` target
  (`npx nx e2e aurelius-atlas-mcp -c ci`); the conftest starts the shared
  infra and leaves it running (DD-223).
- `sonar-project.properties` — key `aureliusenterprise_aurelius-atlas-mcp`
  (DD-897). `tests/` and `e2e/` are the tests paths.
- `tests/` — the unit suite (36 tests, offline): a fake RSA issuer,
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

- `project.json` — `serve` depends on `decrypt`, `certgen` and dev Keycloak;
  the hand-written `e2e` target adds the server and verdicts builds and the
  three infra `up`s (DD-200's target shape). `test`/`build`/`docker-*`/
  `decrypt`/`lint`/`typecheck` are inferred by `tools/plugins/python.ts` from
  `pyproject.toml`, `sourceRoot` and `tests/`.
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-mcp` after changing
  `.env`; CI regenerates plaintext `.env` from `.env.enc`).
- `tls.json` — the app's own certificate for `nx serve` (`nx certgen` runs
  through the tls plugin). The SANs already cover the compose service name and
  localhost, so the standalone piece (`docker/compose.yaml`) reuses the same
  certificate folder; the manifest line lives in `docker/certs.txt`.
- The webapp is the only ingress: its nginx `/mcp` location (static
  `docker/webapp/nginx.conf`, chart template in
  `apps/aurelius-atlas-webapp/nginx.conf.template`) proxies the path with
  buffering off and hour-long reads — no prefix rewrite, because the app serves
  `/mcp` itself (DD-894). The chart's NetworkPolicy admits the webapp pod only
  (MCP-19). Agents never dial this app directly.
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled),
  nonroot, liveness healthcheck that follows the cert pair.
- The caller gate is the shared lib (`aurelius-atlas-auth`): `BearerGate` wraps
  `KeycloakAuth.verify` around the FastMCP ASGI app. Audience `aurelius` in dev
  (the webapp's client, AUX-04): an agent's token is minted like the browser's.
- The write gate reads the caller's claims (`may_write` in `auth.py`) — role
  `atlas-write` in `realm_access.roles` or
  `resource_access.<write_role_client>.roles` (default
  `aurelius-atlas-server`, the catalogue client — MCP-28, DD-898: Keycloak
  namespaces client roles per client, so the audience's entry never carries
  it). A write tool must refuse before any upstream request (MCP-11).
- There is deliberately **no** service identity, OTLP ingest identity, client
  secret, or circuit breaker in this app (ADR 072, DV-208, DD-890). Do not add
  a mint here; upstreams see only the caller's bearer token.
- `sonar-project.properties` is in place with the deployment increment; the
  SonarCloud project `aureliusenterprise_aurelius-atlas-mcp` is created by a
  person before the first analysis (DD-897).
- What landed: the chart, the umbrella join, the standalone piece and the
  webapp proxy (21.2), and the e2e chain with its token probe (21.3 — the
  suite's `.env` carries the shared dev secrets for the stack's `${VAR:?}`
  guards and the writer password the e2e task mints with; the app itself reads
  none of them). The Keycloak realm client never lands — this app has no
  service identity (DV-208, DD-893).

## Removal

Removing the front door removes `apps/aurelius-atlas-mcp` — its root
`pyproject.toml` entries (member, dev group, uv source), the umbrella's
`atlas-mcp` dependency, values block and `Chart.lock` entry, the webapp's
`/mcp` proxy trio (the nginx location in both template copies, the
`mcpService` helper and `mcp`/`nginx.mcpUpstream*` values, and the
placeholder pair in the webapp chart's deployment), the stack piece
(`docker/docker-compose.yaml` include, `stack.env`/`.env.example` and
`certs.txt` lines), the roadmap/spec rows, and the root-test roster entries
(charts aux/umbrella/webapp, standalone pieces/paths/host/images/webapp).
There is no realm client, secret or otel client to unwire (DV-208, DD-893).
`aurelius-atlas-auth` and the SDKs stay — the other apps use them.

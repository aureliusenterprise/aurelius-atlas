# 21.3 The MCP chain proves the front door live

- **Status:** in progress
- **Pull request:** —
- **Records:** DD-898 to DD-900 (in [design.md](./design.md)); continues
  [21.1](../21-1-mcp-api/spec.md) (MCP-01..16), [21.2](../21-2-mcp-deployment/spec.md)
  (MCP-17..24, DD-897)

## Scope

21.1 deferred the e2e chain and 21.2 deferred it again (DD-897). This increment
delivers it: the app runs in a Docker stack beside the real Atlas server and the
real verdicts API, and the suite drives it through a real MCP session. The chain
is also where the write rule gets its live proof — and where that proof found
the write gate read the wrong claim location (MCP-28, DD-898).

| Carrier                                                       | What lands                                                                                    |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `apps/aurelius-atlas-mcp/e2e/compose.mcp.yaml`                | The app's e2e layer over its stack piece (the aux layer shape, ADR 065/066's extension)       |
| `apps/aurelius-atlas-mcp/e2e/docker-compose.yaml`             | The chain stack: the server base at 21009, the verdicts API layer, the app layer              |
| `apps/aurelius-atlas-mcp/e2e/conftest.py`                     | The fixtures: the token probe, the MCP session factory, the writer/reader identities, seeding |
| `apps/aurelius-atlas-mcp/e2e/test__aurelius_atlas_mcp_e2e.py` | The chain suite over the wire                                                                 |
| `apps/aurelius-atlas-mcp/project.json`                        | The `e2e` target with the chain's build/up dependencies (DD-200's target shape)               |
| `apps/aurelius-atlas-mcp/{settings,auth,tools,app}.py`        | The write gate's claim fix (MCP-28, DD-898) and its unit pins                                 |
| `apps/aurelius-atlas-mcp/.env(.enc)`, sonar join              | The chain's env answers, and `e2e/` in `sonar.tests` (MCP-32)                                 |

This increment does not deliver:

| Not delivered                             | It lands in                                                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| A live probe of the webapp's `/mcp` proxy | The webapp's suite (the path is its surface; the proxy's text is already pinned by 21.2's tests). |
| A Keycloak realm client for the app       | Not planned (DV-208, DD-893). The chain's probe proves the caller's token, not a service leg.     |

## Semantics

The chain rules continue the MCP id series. They re-prove 21.1 rules over the
wire where the unit fakes could bake in a false shape (DD-898 is that proof).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MCP-25 | The chain runs the app through an e2e layer that extends its stack piece and states only the e2e differences (the aux layer shape): the proxy network reset, the dev Keycloak issuer on the host, the two upstream legs by their in-network certificate names, no secret keys, no `OTEL_*` keys (MCP-22 carried into the layer).                                                                     |
| MCP-26 | The chain's server sidecar extends the server project's e2e base at host port 21009, loopback-pinned (CIA-03), and accepts the browser's audience plus the verdicts app's own (the app signs its rules leg, VEV-04); the verdicts sidecar extends its own e2e layer; the app itself publishes a random loopback port (DD-897's ladder note: 21005..21008 were taken).                                |
| MCP-27 | Before the stack starts, the suite mints the browser token it will send (public `aurelius` client, password grant) and makes sure it carries the catalogue write role (DD-897's token probe; no leg probe exists, DV-208). A token without the role names the stale-realm remedy (DD-900).                                                                                                           |
| MCP-28 | A write tool reads the write role where Keycloak actually puts it: `realm_access.roles` or `resource_access.aurelius-atlas-server.roles` — the catalogue client's entry, because Keycloak namespaces client roles per client and `atlas-write` belongs to the catalogue client (DD-898; the webapp's editor gate reads the same claim, and the server enforces the same one on the forwarded token). |
| MCP-29 | Over one live MCP session the caller's own token travels (MCP-03 made visible): `server_status` names the caller, and a writer's `save_entity` lands an entity the server authorized from that browser token (MCP-10, MCP-13).                                                                                                                                                                       |
| MCP-30 | A reader's write tool refuses with the MCP tool error and the store stays clean: the refusal happens before the server sees the write (MCP-11, MCP-14's live sibling).                                                                                                                                                                                                                               |
| MCP-31 | `validate_entity` answers live verdicts over a rule seeded through the chain's catalogue (MCP-12 over real upstreams); the read tools (`search_entities`, `get_entity`, `list_types`, `get_type`) answer live data seeded the same way.                                                                                                                                                              |
| MCP-32 | The image re-proves the gate and liveness over the wire: a missing bearer is a 401 with the challenge, and `GET /liveness` answers 204 without a token (MCP-02, MCP-15). The sonar join lists `e2e/` beside `tests/`.                                                                                                                                                                                |

## Java origin

This ports nothing, like 21.1 and 21.2.

## Deviations

None new. The fix of MCP-28 aligns the implementation with MCP-11 as written;
DV-208's posture (no service identity) is proven harder by MCP-25's keyless layer.

## Acceptance

Offline gates, run in the repo root:

```bash
uv run pytest apps/aurelius-atlas-mcp/tests -q                       # write-gate fix pinned (MCP-28)
uv run pytest tests/test__standalone_aux_pieces.py -q                # the e2e layer joins the roster
uv run zensical build --strict
```

The chain gate (verification level 2, Docker + SOPS key):

```bash
npx nx e2e aurelius-atlas-mcp -c ci
```

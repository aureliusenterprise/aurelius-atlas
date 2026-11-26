# 21.1 The Model Context Protocol API

- **Status:** in progress
- **Pull request:** —
- **Records:** [ADR 072](../../../../docs/architecture/adr/072-the-catalogue-answers-agents-through-mcp.md),
  DD-887 to DD-892 (in [design.md](./design.md)), DV-208

## Scope

`apps/aurelius-atlas-mcp` is a new auxiliary API ([ADR 055](../../../../docs/architecture/adr/055-the-lineage-chain-is-a-named-data-surface.md))
that speaks the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) over
Streamable HTTP, built with [FastMCP](https://gofastmcp.com/). An MCP client — an agent
runtime, an IDE assistant, the MCP inspector — connects to `POST /mcp` and finds a small
set of catalogue tools: search, read, lineage, glossary, type system, write, and the
governance verdicts of `aurelius-atlas-validate-entity`.

The app holds no catalogue logic. Every tool call travels to the Atlas server through
`aurelius-atlas-server-client` (8.4) with **the caller's own bearer token**, and to
validate-entity through `aurelius-atlas-validate-entity-client`. The app is a protocol
adapter: JSON-RPC in, Atlas REST out.

This increment delivers:

| Surface      | It answers                                                                       |
| ------------ | -------------------------------------------------------------------------------- |
| `POST /mcp`  | The MCP Streamable HTTP endpoint: tools, and the liveness custom route beside it |
| 12 tools     | The discovery, read, lineage, glossary, typedef, write and verdict tools below   |
| Gate         | The caller's Keycloak bearer token, verified for this app's audience             |
| Dev surfaces | Nothing beyond MCP — the app answers no OpenAPI document                         |

This increment does not deliver:

| Not delivered                        | It lands in                                                                                                                   |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| The Keycloak realm client            | None needed. The app has no service identity — the caller's own token is the only credential (DV-208, DD-893).                |
| The compose piece and the chart      | The deployment increment (21.2): the stack piece, the chart, and the webapp's /mcp proxy (MCP-17 to MCP-23).                  |
| The e2e suite standing a real server | The deployment chain's increment (21.3, DD-897). Unit tests prove the rules against a mock upstream.                          |
| stdio transport                      | Not planned. The app is a shared service (DD-887).                                                                            |
| The 2.x aux-client parity scenarios  | Not applicable. The app ports no Java class; its upstream calls are the client libraries' contracts, proven at home (DV-208). |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                  |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MCP-01 | `POST /mcp` answers the MCP Streamable HTTP protocol. The endpoint is mounted at `/mcp` on the app's port.                                                                                                                                                            |
| MCP-02 | Every MCP request carries a bearer token that verifies for the app's audience through `aurelius-atlas-auth` (AUX-02..AUX-05). A missing or bad token is refused before any tool runs; the catalogue is never called anonymously.                                      |
| MCP-03 | Every catalogue call a tool makes carries the caller's own token, never a service identity of the app (the validate-entity leg's VEV-04 posture deliberately does not hold here, DV-208).                                                                             |
| MCP-04 | Tools advertise through MCP: `search_entities`, `get_entity`, `get_lineage`, `search_glossary`, `get_type`, `list_types`, `save_entity`, `add_classifications`, `remove_classification`, `delete_entity`, `validate_entity`, `server_status`.                         |
| MCP-05 | `search_entities(query, type_name?, limit, offset)` searches basic (free-text `query`) and answers compact entity headers: guid, display name, type, classifications, status, qualified name — never whole entities.                                                  |
| MCP-06 | `get_entity(guid)` answers the whole entity; `get_entity(type_name, unique_attributes)` answers it by unique attributes. Both reject a call that gives neither locator, and both give both.                                                                           |
| MCP-07 | `get_lineage(guid, depth?, direction?)` answers the lineage graph: nodes as headers and edges as relations, bounded by depth and direction.                                                                                                                           |
| MCP-08 | `search_glossary(glossary_guid, query?, limit, offset)` answers the glossary's term headers; `search_glossary` with no query pages all terms.                                                                                                                         |
| MCP-09 | `get_type(name)` answers one typedef; `list_types(kind)` answers the typedef headers of one kind (`entity`, `classification`, `relationship`, `struct`, `enum`, `business-metadata`).                                                                                 |
| MCP-10 | `save_entity(entity)` creates or updates the entity body (EWR-02); `add_classifications(guid, classifications)` and `remove_classification(guid, name)` edit classifications; `delete_entity(guid, hard?)` deletes (EDL).                                             |
| MCP-11 | A write tool refuses its call — the MCP tool error, no upstream request — unless the caller's token carries the write role (`atlas-write`), verified the way `aurelius-atlas-auth` verifies it.                                                                       |
| MCP-12 | `validate_entity(draft)` answers the live governance verdicts of validate-entity over the draft (VEV-02); the verdicts travel as the verdict document.                                                                                                                |
| MCP-13 | `server_status()` answers the server's version, status and the caller's session (ADM). It proves the chain, not the framework: it is the tool a client calls first.                                                                                                   |
| MCP-14 | An upstream failure is an MCP tool error whose text names the upstream status and message (CL-04's parsed `{errorCode, errorMessage}`); an unreachable upstream names the transport failure. A tool never answers Atlas's raw body and never invents an empty answer. |
| MCP-15 | `GET /liveness` answers `204` without a token (the container healthcheck, VE-04's posture). Custom routes are outside the MCP auth gate by FastMCP's design.                                                                                                          |
| MCP-16 | The app's settings arrive as `AURELIUS_ATLAS_MCP_`-prefixed environment variables through pydantic-settings (DD-197's channel); the auth block is required, the server base URL defaults to the dev server.                                                           |

## Java origin

This ports nothing. Apache Atlas 2.4.0 has no MCP server, and FastMCP is the chosen
framework, not ported code ([ADR 045](../../../../docs/architecture/adr/045-conventions-are-borrowed-before-they-are-invented.md)).
The catalogue behaviour behind each tool is already ported and specified by the
server increments the client libraries cite (8.4, 8.9–8.12).

## Deviations

| Id     | Deviation from Apache Atlas                                                                                                                                                                                                                                                             |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DV-208 | Aurelius Atlas answers agents over MCP, which Atlas 2.4.0 does not offer at all. Unlike the 8.x aux APIs, the MCP app forwards the caller's token to the catalogue instead of signing with its own service identity, because an agent session is a user acting, not a batch job acting. |

## Acceptance

Unit tests, run offline:

```bash
uv run pytest apps/aurelius-atlas-mcp/tests
```

| Test file                    | Proves                                                 |
| ---------------------------- | ------------------------------------------------------ |
| `tests/test__settings.py`    | MCP-16                                                 |
| `tests/test__app.py`         | MCP-01, MCP-02, MCP-15 — the gate and the health route |
| `tests/test__tools_read.py`  | MCP-05..MCP-09, MCP-13, MCP-14 against a mock upstream |
| `tests/test__tools_write.py` | MCP-10..MCP-12, MCP-11's refusal                       |

Every test names its functions and rules with `@pytest.mark.covers(..., rules=["MCP-NN"])`
(ADR 056); `uv run aurelius-atlas-trace check` reports the gaps.

# aurelius-atlas-mcp

The Aurelius Atlas MCP API: an agent-facing front door over the catalogue. AI
assistants reach the catalogue through the Model Context Protocol (MCP) over
Streamable HTTP instead of learning the raw REST surface
([ADR 072](../../docs/architecture/adr/072-the-catalogue-answers-agents-through-mcp.md),
increment [21.1](specs/21-1-mcp-api/spec.md)).

The app holds no catalogue logic of its own. Twelve thin tools forward to the
Atlas server and the validate-entity API through the client libraries:
`search_entities`, `get_entity`, `get_lineage`, `search_glossary`, `get_type`,
`list_types`, `save_entity`, `add_classifications`, `remove_classification`,
`delete_entity`, `validate_entity`, and `server_status` (MCP-04). Every call
carries the **caller's own** bearer token — the app never signs with a service
identity — so the catalogue sees the person behind the agent (MCP-03,
[DV-208](../../docs/architecture/conversion/deviations.md)). A missing or bad
token is refused before any tool runs (MCP-02), and a write tool refuses unless
the token carries the `atlas-write` role (MCP-11).

## Surface

| Endpoint        | Auth            | Answers                                                            |
| --------------- | --------------- | ------------------------------------------------------------------ |
| `POST /mcp`     | Keycloak bearer | The MCP Streamable HTTP protocol; tools answer as MCP tool results |
| `GET /liveness` | –               | `204` while the app runs (the container healthcheck, MCP-15)       |

There is no OpenAPI document and no other route: the protocol itself describes
the surface (DD-887).

## Run

```bash
npx nx serve aurelius-atlas-mcp          # https://localhost:21005, dev Keycloak up
uv run pytest apps/aurelius-atlas-mcp/tests   # the unit suite (offline)
```

`nx serve` starts the dev Keycloak; point an MCP client (for example the MCP
inspector) at `https://localhost:21005/mcp` with a bearer token minted for the
webapp's `aurelius` client. The tools call the dev server
(`https://localhost:21000`) and validate-entity (`https://localhost:21003`);
start those with `nx serve` if you want the catalogue answers behind the tools.

## Settings

Every setting is an `AURELIUS_ATLAS_MCP_`-prefixed environment variable read
through pydantic-settings (MCP-16). The dev values live in `.env` (decrypted
from `.env.enc`); `aurelius_atlas_mcp/settings.py` documents each field. The
auth block (`AURELIUS_ATLAS_MCP_AUTH_SERVER_URL`) is the only required setting;
the two upstream URLs default to the dev services.

## Not wired yet

The deployment increment for this app still owes: the Keycloak realm client and
its compose piece, the Helm chart, the e2e suite that stands a real server, and
the SonarCloud project. See the spec's "Not delivered" table.

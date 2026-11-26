# 21.2 The MCP service deploys like its siblings

- **Status:** in progress
- **Pull request:** —
- **Records:** DD-893 to DD-897 (in [design.md](./design.md)); continues
  [21.1](../21-1-mcp-api/spec.md) (MCP-01 to MCP-16, ADR 072, DV-208)

## Scope

Increment 21.1 built the MCP app and stated that its realm client, compose
piece, chart, and e2e chain were not delivered. This increment delivers
everything that makes the app deployable, except the e2e chain, which is its
own increment (21.3):

| Carrier                                            | What lands                                                                                                   |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `apps/aurelius-atlas-mcp/docker/compose.yaml`      | The standalone stack's MCP piece (ADR 065, DD-674's shape)                                                   |
| `docker/` umbrella                                 | The piece's include, `MCP_CERTS_DIR`, `MCP_IMAGE`, the certgen line, and the webapp proxy's `/mcp/` location |
| `apps/aurelius-atlas-mcp/helm/`                    | The chart (the aux copy per DD-290): deployment, service, SA, PDB, Certificate, NetworkPolicy, validation    |
| `apps/aurelius-atlas-webapp/helm/`                 | The `/mcp/` proxy location behind the webapp, with the streaming posture the protocol needs                  |
| `helm/` umbrella                                   | The chart dependency and its values block — no secret join (DD-893)                                          |
| `apps/aurelius-atlas-mcp/sonar-project.properties` | The SonarCloud analysis join, after the project key exists in the org (DD-897)                               |

This increment does not deliver:

| Not delivered                                               | It lands in                                                                                                                   |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| The e2e chain (real server and verdicts API beside the app) | Increment 21.3 (DD-897's sibling note; the spec's chain rules, host port 21009 — 21005 is the quality scanner's e2e sidecar). |
| A Keycloak realm client for the app                         | Not planned. The app holds no service identity (DV-208, DD-893), so there is no client to import.                             |
| OTLP ingest for the app                                     | Not planned. The ingest identity is the service's own credential (DD-196), and the app has none (ADR 072).                    |

## Semantics

The deployment rules continue the MCP id series. Chart internals reuse the
CHT ids the aux suite already pins (ADR 002: the helm specs own those).

| Id     | Rule                                                                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MCP-17 | The standalone stack runs the app as a piece: `network_mode: service:proxy`, no published port, the stack's issuer (`https://localhost:9000/auth/`), realm `aurelius-atlas`, audience `aurelius`, and the guarded `MCP_CERTS_DIR` volume (DD-674's shape). |
| MCP-18 | The piece names both upstream legs (`AURELIUS_ATLAS_MCP_SERVER_BASE_URL`, `AURELIUS_ATLAS_MCP_VALIDATE_ENTITY_BASE_URL`) and names **no** secret: no client secret, no token URL, no `OTEL_*` key (DV-208).                                                |
| MCP-19 | The webapp's proxy answers `/mcp/` for agents: the standalone gateway's webapp container and the chart's webapp pod both route it to this Service with buffering off and a long read timeout, so streamed responses flow (DD-894).                         |
| MCP-20 | The chart renders the aux shape (CHT-02): port 21005, prefix `AURELIUS_ATLAS_MCP_`, the mounted Certificate pair at `/etc/aurelius-atlas/tls` (CHT-27), probes on `/liveness`, nonroot 65532.                                                              |
| MCP-21 | The chart joins both siblings from the same release: `SERVER_BASE_URL` from the `atlas` join (21000) and `VALIDATE_ENTITY_BASE_URL` from the `validateEntity` join (21003), each overridable by name (CHT-28's siblingService rule).                       |
| MCP-22 | The chart renders **no** credential: no `credentialSecrets` key, no Secret env, no `TOKEN_URL`, no OTEL block even when `telemetry.enabled` is set on the umbrella (DD-893, DV-208).                                                                       |
| MCP-23 | The umbrella registers the chart as a dependency with the pinned version and enables it by default without a secret block (DD-288).                                                                                                                        |
| MCP-24 | `nx sonar aurelius-atlas-mcp` analyses the package with its tests and both sarif reports, under the org's project key (the CI join every app has).                                                                                                         |

## Java origin

This ports nothing, like 21.1. The deployment shape is the workspace's own
aux-API convention (8.x, 10.x), not Apache Atlas's.

## Deviations

None new. DV-208 already covers the posture this increment keeps visible in
the chart and piece: no service identity anywhere (DD-893).

## Acceptance

Offline gates, run in the repo root:

```bash
uv run pytest tests/test__charts_aux.py tests/test__charts_umbrella.py tests/test__charts_webapp.py tests/test__standalone_aux_pieces.py tests/test__standalone_paths.py -q
uv run pytest apps/aurelius-atlas-mcp/tests -q   # unchanged app rules still hold
uv run zensical build --strict
```

The root chart tests name the rules with `@pytest.mark.covers(rules=["MCP-NN"])`
where the rule is new here, and the existing CHT pins extend over the new chart
through the `AUX_CHARTS` roster. `nx helm-config-scan aurelius-atlas-mcp`
produces the `helm-misconfigs.json` artifact for the sonar job.

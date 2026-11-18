# 17.1 Infrastructure components live at the repository root

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 066 (Proposed, here); DD-667 to DD-677 (here); relies on
  [ADR 065](../../../docs/architecture/adr/065-compose-stacks-that-deploy-the-whole-system-live-at-the-root.md)
  (the compose fragments and the root `docker/`), ADR 057 (charts as the delivery), ADR 051

The `dev/` folder holds the Elasticsearch, Keycloak and observability slices. Each of them already
carries both ways to run its component: a Helm chart that the umbrella installs in production (ADR 057),
and a compose stack that `nx serve` and the e2e suites start. The name says "dev" while half of its
content is production. The standalone stack grew its own second copies of the store and the identity
provider, so one component is described twice and drifts twice. This increment promotes the folder to
`infra/`, renames its projects to match, and lets the standalone stack borrow the Elasticsearch and
Keycloak services instead of owning copies.

## Scope

- The promotion: `dev/elasticsearch`, `dev/keycloak` and `dev/observability` become
  `infra/elasticsearch`, `infra/keycloak` and `infra/observability`, with their Nx project names,
  compose project names and Docker network names renamed from `aurelius-atlas-dev-*` to
  `aurelius-atlas-infra-*` (IRT-01, IRT-02).
- The rewiring that follows the move: the umbrella chart's `file://` dependencies and lock, the root
  `project.json` inputs, every `dependsOn`, every live path and name in source and docs (IRT-03).
- The standalone stack's store and identity provider: the fragments `docker/elasticsearch/` and
  `docker/keycloak/` extend the infra services, so the stack no longer owns an Elasticsearch or a
  Keycloak definition of its own (IRT-04 to IRT-07).
- The stack's Keycloak gains the production topology: its own Postgres, the realm `aurelius-atlas`
  imported behind the proxy at `/auth` (IRT-06, DD-673).
- The aux services join the stack: the extractor, the lineage API and the validator own a compose
  piece each beside their project, the umbrella includes them, and each project's e2e file layers
  over its piece (IRT-10, DD-674). The webapp's e2e service extends its own piece too.
- The stack gains its own telemetry: the observability piece joins the umbrella and extends the
  infra slice, with the collector's configuration forked to trust the stack's issuer from a file,
  and every producer wired to it (IRT-11, DD-675).
- The gateway joins them as a piece: the proxy and its nginx config move to `docker/gateway/`, so
  the umbrella holds no service of its own (IRT-12, DD-677).

Not delivered, with the increment that will:

| Not delivered                                                | Lands with  |
| ------------------------------------------------------------ | ----------- |
| Publishing a compose stack as a delivery artifact            | not planned |
| Retiring `dev/`'s metrics pullers or the dev networks' shape | not planned |

The folder `infra/arc/` (the cloud-shape tooling) already lives at `infra/` and stays as it is. This
increment adds the components beside it.

## Semantics

"An infrastructure component" is a slice whose Helm chart the umbrella installs: Elasticsearch,
Keycloak, observability. "The infra compose" of a component is the `docker-compose.yaml` beside its
chart. "The stack" is the standalone compose stack at `docker/` (ADR 065). "Extends" is the compose
`extends` clause: a service copies another service's definition from another file and overrides parts
of it.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| IRT-01 | An infrastructure component lives at `infra/<name>/` at the repository root, beside the root `helm/` and `docker/`: its compose, its configuration and certificates, its shared assets (the Keycloak `aurelius` theme), its Helm chart, and its `.env`/`.env.enc`. The name `dev/` no longer exists. (DD-667)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| IRT-02 | Each component's Nx project is `aurelius-atlas-infra-<name>`, its compose project is `aurelius-atlas-infra-<name>`, and its Docker network is `aurelius-atlas-infra-<name>-network`. `nx up aurelius-atlas-infra-elasticsearch` and `nx up aurelius-atlas-infra-keycloak` start what `nx up aurelius-atlas-dev-*` started, with the same images, ports and configuration. (DD-667)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| IRT-03 | No live file names the old paths or the old names. The accepted records of earlier increments, the design-log archive, and the accepted specs keep the text as written, and ADR 066 is the pointer forward. (DD-672)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| IRT-04 | The umbrella chart's component dependencies resolve to `infra/<name>/helm`, and `helm dependency update` and the chart-contract suite pass unchanged. (DD-667)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| IRT-05 | The stack's store is the infra Elasticsearch service, extended: same image pin, configuration, roles, certificate, healthcheck, java agent and ulimits; no published port; the stack's own named volumes; the heap and memory cap the stack states; the server's password placeholder, one placeholder for both services. The chown one shot is extended the same way. (DD-668, DD-669)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| IRT-06 | The stack's identity provider is the infra Keycloak service and its Postgres, extended: Postgres-backed, the theme mounted, no published port, its own named volumes, booted in production mode like the chart with a build one shot whose output the start mounts (DD-676). Its realm is `aurelius-atlas` alone, imported from `docker/keycloak/aurelius-atlas.json`, served at `https://localhost:9000/auth` behind the proxy, so the issuer the server verifies does not change. The realm carries the production realm's posture: the service identities with placeholder secrets, and one person, the platform operator `operator`, a read member of `operators` holding the operator role (DD-670, DD-673, DD-680). A tenant's users are made by the profile tenancy's one shot when it provisions the tenant, never in the realm file (DD-680). Its native OTLP push rides the stack's own collector's legacy leg (DD-675). |
| IRT-07 | The stack runs with three env-files: `apps/aurelius-atlas-server/.env`, `infra/keycloak/.env` and `infra/elasticsearch/.env`. An `extends` base interpolates with the consuming project's environment, so the base's required variables must resolve even where the fragment replaces the value. (DD-669)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| IRT-08 | The stack's compose reads as the merged stack: `tests/conftest.py` resolves `include` and `extends` as compose does, and the standalone tests pin the merged services. A named volume a fragment needs is declared in that fragment. (DD-671)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| IRT-09 | The dev workflow keeps its commands: `nx serve` chains the infra projects' `up` targets, the e2e suites join `aurelius-atlas-infra-<name>-network` as external, and no suite restarts a shared infra service (DD-223). (DD-667)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| IRT-10 | The extractor, the lineage API and the validator each own a piece at `apps/<project>/docker/compose.yaml` with their standalone issuer, realm and audience, and the umbrella includes it always on. Each aux project's e2e file and the webapp's e2e file `extends` its own piece and state only the test's differences. (DD-674)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| IRT-11 | The umbrella includes `docker/observability/compose.yaml` always on: the collector, Prometheus, Loki, Tempo and Grafana, each the infra observability slice's service extended, with the stack's own named volumes and no collector host publish. The collector's configuration is forked and validates one issuer, `https://localhost:9000/auth/realms/aurelius-atlas`, from a JWKS file the `jwks-fetch` one shot writes after Keycloak is healthy; the collector starts only after it. The server and the three aux apps mint through the stack's issuer for the per-service leg, Keycloak and the webapp's edge carry the shared bearer to the legacy leg, the proxy routes `/otel/` to the collector's browser leg, and the realm carries the four `otel-*` ingest clients and the `otel-ingest` scope on `aurelius`. (DD-675)                                                                                                |
| IRT-12 | The gateway is a piece like the other root-owned four: `docker/gateway/compose.yaml` defines the `proxy` (the stack's only published port, loopback 9000) and `docker/gateway/nginx.conf` holds its routes. The umbrella names the project and includes every piece; it holds no service of its own. (DD-677)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Java origin

None. This increment ports no Atlas behaviour. It moves Aurelius infrastructure that surrounds the port
(ADR 066's placement, ADR 065's fragments).

## Deviations

None new. Apache Atlas's single-deployment, single-domain topology (its embedded H2 and its bundled
Elasticsearch) stays recorded as the deviation of ADR 053 and ADR 054. The stack's Keycloak moves
closer to Atlas's simplicity, not away from it: the H2 copy this increment deletes was the deviation.

## Acceptance

- The root chart-contract suite: `uv run pytest tests` (316+ tests, no Docker daemon). SST-, DMO-,
  SKT-, EMB-, WPT- and TRM- rules re-pin against the merged stack (IRT-05 to IRT-08); the rule ids
  named in specs 9.5b to 9.5e, 11.2 and 15.x keep their tests.
- `docker compose -f docker/docker-compose.yaml --env-file apps/aurelius-atlas-server/.env --env-file
infra/keycloak/.env --env-file infra/elasticsearch/.env config --quiet` (IRT-07).
- Level 2: `nx up aurelius-atlas-infra-elasticsearch`, `nx up aurelius-atlas-infra-keycloak`, and the
  stack `up` with a sign-in and the sample import (the commands in `docker/README.md`).
- The rename sweep: `grep -rn "aurelius-atlas-dev\|dev/elasticsearch\|dev/keycloak\|dev/observability"
--exclude-dir=site` returns only historical records (IRT-03).
- The chart gates: `nx affected -t test e2e -c ci` as for any change.

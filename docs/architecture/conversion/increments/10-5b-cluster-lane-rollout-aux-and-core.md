# 10.5b Cluster lane rollout: the lane library, all suites, and the single lane

- **Status:** in progress
- **Pull request:** — (stacked on the 10.5 POC line, #187/#189)
- **Records:** DD-282 (adds), DD-283 (adds; supersedes the dual-lane clauses
  of DD-280/DD-282), DD-284 (adds); relies on DD-280 (the POC whose shapes
  this generalises), DD-281 (the retirements that shrink what must migrate),
  DD-265 (relies on: the CoreDNS split-horizon rewrite the aux dials mirror
  in-cluster), DD-197 (relies on: `KeycloakAuth`'s audience check the
  overlay answers), DD-223 (relies on: the namespaced core aliases the shared
  cluster store rides), DD-019 (supersedes its "examples stay" trigger for
  the two example apps and the example lib)

## Scope

The POC (10.5, DD-280) proved one suite on the deployment and left the
question it exists to answer answered; this increment acts on the verdict for
every suite that has a deployed future, extracts the POC's lane machinery into
a shared library so each suite buys the lane instead of rebuilding it, and —
once the last stack was deleted — collapses the dual-lane gate to one lane
(the webapp that was 10.5c, and the lineage-model 10.5d retirement, folded in
here; DD-283/284).

- **The lane library** (`libs/python/aurelius-atlas-cluster-lane`, CHT-103):
  a workspace dev-group pytest helper owning everything lane-shaped — the
  fail-fast `cluster` gate (helm `deployed`, the Gateway address, the chart CA
  read from the Secret), the process-local
  `socket.getaddrinfo` shim, a `ServiceForward` port-forward helper with
  honest-TLS dials, `mint_token`, and the cluster credential reads (Secret
  passwords). Conftests keep only what is theirs: which services, which clients.
- **The aux twins** (`aurelius-atlas-data2model`, `aurelius-atlas-validate-
entity`, CHT-104): each e2e conftest grows the cluster lane — the app
  dialled at its Service's real name through a port-forward (SAN-honest TLS),
  the token minted through `keycloak.atlas.test` (the same issuer origin the
  pods themselves verify against), the mint password read from the
  `atlas-keycloak-users` Secret. Both suites' tests are
  data-independent (extract-from-body, static mock), so nothing needs
  seeding.
- **The audience overlay** (CHT-105): the suites mint `azp=aurelius` tokens;
  the aux charts default `AUTH_AUDIENCE` to their own service name, so the
  minikube environment overrides both aux audiences to `aurelius` — an
  environment-values decision (CHT-04), pinned by a new chart-render guard.
  No chart or shipped default changes.
- **The core store suite** (`libs/python/aurelius-atlas-core`, CHT-104):
  23 tests that talk to Elasticsearch and nothing else gain the lane by
  swapping one fixture — `dev_settings` points at a port-forwarded
  `svc/atlas-elasticsearch` dialled at its Service FQDN (SAN-honest), the
  `elastic` password from the `atlas-elasticsearch` Secret, the chart CA.
  The namespaced-alias discipline (DD-223) makes the shared cluster store
  safe for these writes.
- **Browser DNS** (CHT-106): `install.sh` grows a `hosts` step (and
  subcommand) that maintains a fenced `/etc/hosts` block mapping
  `atlas.<domain>`/`keycloak.<domain>` to the live Gateway address, and the
  devcontainer refreshes it at every container start when a cluster is live.
  The Python suites never need it (the shim covers them); it serves the
  Playwright browsers and `page.request`, and it is what lets the webapp
  migration ride the same install.
- **The webapp suite** (`aurelius-atlas-webapp`, CHT-107, DD-284): the hardest
  migration (DD-280's ranking) — 33 Playwright tests driving a browser through
  the realm login at the real edge (`https://atlas.atlas.test`), an
  authenticated storage state, three collector legs plus Tempo over
  port-forwards with pinned loopback ports, and a footer test that reads the
  _deployed_ `/config.json` rather than a compose fixture.
- **The realm browser origins** (CHT-107): `install.sh realm-origins` registers
  the edge origin on the live `aurelius` client (redirectUris, post-logout,
  webOrigins) through the admin API — read-merge-write, idempotent, never
  appending to a `*`-covered list. The chart's realm asset stays loopback-only.
- **The single-lane collapse** (DD-283): with the last compose stack deleted, the
  `ATLAS_E2E_TARGET` gate and `lane_target()` leave the library; a migrated
  suite's `e2e` target is the cluster suite (the plugin's inferred deps cancelled
  by an explicit `"dependsOn": []`), and its `e2e/docker-compose.yaml` is deleted.
- **The lineage-model suite retires** (DD-284): its compose fixtures were the
  test, so it has no cluster-shaped future; the `e2e/` directory and target are
  deleted and its rules stay covered by units and parity scenarios (noted in 8-2).
- **The template examples leave** (DD-284): the two example apps and their
  library go early (superseding DD-019's trigger), with their compose stacks,
  realm origins, dashboards, api-reference pages, uv members, and the
  data-access example client.

This increment explicitly does **not** deliver: CI wiring for the cluster
suites (they need a live minikube umbrella that CI does not have — the DD-283
deferral, closing in the next increment); prod-realm runs. The compose e2e
stacks under `apps/*/e2e/` are retired here; the `dev/*` stacks stay as the
local `nx serve` world.

## Semantics

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CHT-103 | `aurelius-atlas-cluster-lane` owns the lane machinery as importable fixtures and helpers: the `cluster` session fixture gates (`deployed` or fail-fast naming `install.sh up`), reads the Gateway address and the chart CA (Secret `aurelius-atlas-selfsigned-ca`), and installs the `*.atlas.test` + Service-FQDN resolver shim; `SecretReader` reads Secret keys at run time; `install_cluster_fixtures` installs the session fixtures so a conftest names only its own suite shape. A migrated suite has exactly one lane — the deployment — so there is no env gate (the DD-280/282 `ATLAS_E2E_TARGET` gate is retired, DD-283); consumers opt in by calling `install_cluster_fixtures` in their own conftest, so a plain `pytest`/unit run never autoloads kubectl-shaped code at collection time.                                                |
| CHT-104 | A cluster-mode dial uses the Service's real name: `ServiceForward` port-forwards `svc/<name>` to a free loopback port and the shim maps `<service>.<ns>.svc.cluster.local` (and the `<domain>` hosts) onto it, so the URL, SNI, and verified SAN stay honest while nothing new is exposed to the host. The dial URL names the forward's own port and the shim rewrites the host alone — a host+port rewrite would be silently dropped by the async HTTP stack (anyio connects on the URL's port), landing the dial beside the forward; the URL's port is the loopback port, the hostname is the real FQDN, which is what the SAN covers. No cluster-mode fixture ever dials a bare `127.0.0.1` name where a SAN-honest name exists — except baked-dashboard Playwright dials, which ride `ignore_https_errors` (ADR 039) exactly as the POC left them. |
| CHT-105 | The minikube environment carries `AURELIUS_ATLAS_{DATA2MODEL,VALIDATE_ENTITY}_AUTH_AUDIENCE: aurelius` in the aux `config:` blocks (flat map, CHT-04), matching the `aurelius` client's tokens the suites mint; a chart-render guard pins both values on the minikube overlay, and the shipped chart defaults (per-service audiences) are untouched — no environment file outside `helm/environments/` carries the override.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| CHT-106 | `install.sh hosts` rewrites a `# BEGIN/END aurelius-atlas-cluster` block in `/etc/hosts` mapping `atlas.<domain>` and `keycloak.<domain>` to the Gateway address it reads live (fail if absent); `up` runs it after readiness; the devcontainer `postStartCommand` runs it best-effort (a live cluster is not a container-start precondition). The block is the script's own — it never edits lines outside the fence, and re-runs converge on the current Gateway IP.                                                                                                                                                                                                                                                                                                                                                                                 |
| CHT-107 | `install.sh realm-origins` (wired into `up`) registers the edge on the live realm's `aurelius` client through the admin API: it appends `https://<edge-host>/*` to redirectUris and post-logout redirectUris and `https://<edge-host>` to webOrigins, read-merge-write - PUTting only what is missing (re-runs are idempotent), and never appending to a list already covered by a bare `*` (Keycloak rejects that with a 400). The chart's realm asset stays the loopback-only baseline; the cluster's live client is a converged superset owned by this script. A missing client fails loudly.                                                                                                                                                                                                                                                       |

## Java origin

No Java twin: this is Aurelius test infrastructure (the e2e suites are
Aurelius-side, ADR 051's parity harness consumes them; Apache Atlas tests
against an embedded JanusGraph stack and has no deployment axis).

## Deviations

The aux audience overlay is environment configuration, not a behavioural
deviation — the shipped charts and DV-74/DV-75's shapes are untouched. Two
process deviations this increment carries on purpose:

- **The e2e suites leave CI** (DD-283 call 4). A migrated suite now needs a
  live minikube umbrella, which CI does not have, so the workflows drop `e2e`
  from their affected/run-many sets. The gate moves local: every migrated
  suite green against one live release before CI changes shape. This is the
  POC's CI deferral (DD-280) still standing, widened — closing it needs a
  cluster-shaped runner, in the next increment.
- **The template examples leave ahead of DD-019's "after the plan" trigger**
  (DD-284 call 5). They were reference material only; the plan's remaining
  work never consults them, and they were the largest source of stale wiring.

## Acceptance

Unit (library, no cluster):

- `libs/python/aurelius-atlas-cluster-lane/tests/` — the gate's fail-fast
  message naming `install.sh up`, the shim's bytes/str host matching, its
  host-only registration for a forward and its (host, port) pair shape for
  callers that need a port moved, `SecretReader`'s decoding,
  `ServiceForward`'s free-port and pinned-port command shapes, the hosts-file
  fence edit (tmp file, both first-insert and converge-on-churn paths), and
  `ensure_browser_origins`'s read-merge-write (adds the edge origin, is
  idempotent on a covered client, leaves a `*`-covered list alone, fails loudly
  on a missing client). Marked
  `@pytest.mark.covers(..., rules=["CHT-103", "CHT-104", "CHT-106", "CHT-107"])`
  on the named functions (ADR 056).

Chart (rendered, no cluster):

- `tests/test__charts_aux.py` — new: the minikube overlay render carries both
  aux `AUTH_AUDIENCE=aurelius` envs (CHT-105) while the default render keeps
  the per-service audiences.
- `tests/test__charts_webapp.py` / `tests/test__charts_observability.py` —
  shrink to the surviving assets: the compose e2e `nginx.conf`/`config.json`
  byte-copy guards retire, the shipped-template/chart-copy guards and the
  five-dashboard count stay.

E2E (the single cluster lane — `tools/cluster/install.sh up` + `realm-origins`

- `hosts` as preconditions; the compose lane is retired, DD-283):

- `nx e2e` on the five migrated projects (server 37, data2model 7,
  validate-entity 7, core 23, webapp 105 across chromium/firefox/webkit), green
  cold (fresh `up`) and warm (rerun), against the same release — the twins'
  assertions unchanged, the core suite riding the shared store, the server
  suite unchanged through the refactored conftest, the webapp driving the realm
  login through the edge and reading the deployed `/config.json`.
- Negative: an `e2e` run against a down release fails at the gate within
  seconds, naming `install.sh up` (CHT-103's fail-fast).
- Hosts: `install.sh hosts` against a live cluster writes the fenced block with
  the live Gateway IP; re-running after an IP change replaces it and touches
  nothing outside the fence (CHT-106).
- Realm origins: `install.sh realm-origins` against a live cluster registers
  the edge origin once, is idempotent on a re-run, and the auth URL then serves
  a `200` for the edge `redirect_uri` (CHT-107).
- Retirement: `nx show project aurelius-atlas-lineage-model` lists no `e2e`
  target; `nx show projects` lists no example-app project; `uv lock` and the Nx
  graph are clean without them (DD-284).

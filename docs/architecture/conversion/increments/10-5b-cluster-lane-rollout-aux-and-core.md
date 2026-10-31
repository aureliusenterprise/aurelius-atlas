# 10.5b Cluster lane rollout (part 1): the lane library, the aux twins, the core store suite

- **Status:** in progress
- **Pull request:** — (stacked on the 10.5 POC line, #187/#189)
- **Records:** DD-282 (adds); relies on DD-280 (the POC whose shapes this
  generalises), DD-281 (the retirements that shrink what must migrate),
  DD-265 (relies on: the CoreDNS split-horizon rewrite the aux dials mirror
  in-cluster), DD-197 (relies on: `KeycloakAuth`'s audience check the
  overlay answers), DD-223 (relies on: the namespaced core aliases the shared
  cluster store rides)

## Scope

The POC (10.5, DD-280) proved one suite on the deployment and left the
question it exists to answer answered; this increment acts on the verdict for
the three suites whose compose coupling is small enough to move first, and
extracts the POC's lane machinery into a shared library so each later suite
(webapp 10.5c, lineage-model 10.5d) buys the lane instead of rebuilding it.

- **The lane library** (`libs/python/aurelius-atlas-cluster-lane`, CHT-103):
  a workspace dev-group pytest helper owning everything lane-shaped — the
  `ATLAS_E2E_TARGET` env gate, the fail-fast `cluster` gate (helm `deployed`,
  the Gateway address, the chart CA read from the Secret), the process-local
  `socket.getaddrinfo` shim, a `ServiceForward` port-forward helper with
  honest-TLS dials, and the cluster credential reads (Secret passwords).
  Conftests keep only what is theirs: which services, which clients.
- **The aux twins** (`aurelius-atlas-data2model`, `aurelius-atlas-validate-
entity`, CHT-104): each e2e conftest grows the cluster lane — the app
  dialled at its Service's real name through a port-forward (SAN-honest TLS),
  the token minted through `keycloak.atlas.test` (the same issuer origin the
  pods themselves verify against), the mint password read from the
  `atlas-keycloak-users` Secret in cluster mode. Both suites' tests are
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
  Playwright browsers and `page.request`, and it is what lets the 10.5c
  webapp migration ride the same install.

This increment explicitly does **not** deliver: CI wiring (unchanged from the
POC's cut — compose stays CI's lane; the targets are named outside the plugin
inference and no workflow references them); the webapp (10.5c) or
lineage-model (10.5d) suites; retiring any compose stack; prod-realm runs.

## Semantics

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CHT-103 | `aurelius-atlas-cluster-lane` owns the lane machinery as importable fixtures and helpers: `lane_target()` reads `ATLAS_E2E_TARGET` (default `compose` — every existing invocation stays byte-identical), the `cluster` session fixture gates (`deployed` or fail-fast naming `install.sh up`), reads the Gateway address and the chart CA (Secret `aurelius-atlas-selfsigned-ca`), and installs the `*.atlas.test` + Service-FQDN resolver shim; `SecretReader` reads Secret keys at run time. Compose-mode consumers must never import kubectl-shaped code paths at call time.                                                                                                                                                                                                                                                                        |
| CHT-104 | A cluster-mode dial uses the Service's real name: `ServiceForward` port-forwards `svc/<name>` to a free loopback port and the shim maps `<service>.<ns>.svc.cluster.local` (and the `<domain>` hosts) onto it, so the URL, SNI, and verified SAN stay honest while nothing new is exposed to the host. The dial URL names the forward's own port and the shim rewrites the host alone — a host+port rewrite would be silently dropped by the async HTTP stack (anyio connects on the URL's port), landing the dial beside the forward; the URL's port is the loopback port, the hostname is the real FQDN, which is what the SAN covers. No cluster-mode fixture ever dials a bare `127.0.0.1` name where a SAN-honest name exists — except baked-dashboard Playwright dials, which ride `ignore_https_errors` (ADR 039) exactly as the POC left them. |
| CHT-105 | The minikube environment carries `AURELIUS_ATLAS_{DATA2MODEL,VALIDATE_ENTITY}_AUTH_AUDIENCE: aurelius` in the aux `config:` blocks (flat map, CHT-04), matching the `aurelius` client's tokens the suites mint; a chart-render guard pins both values on the minikube overlay, and the shipped chart defaults (per-service audiences) are untouched — no environment file outside `helm/environments/` carries the override.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| CHT-106 | `install.sh hosts` rewrites a `# BEGIN/END aurelius-atlas-cluster` block in `/etc/hosts` mapping `atlas.<domain>` and `keycloak.<domain>` to the Gateway address it reads live (fail if absent); `up` runs it after readiness; the devcontainer `postStartCommand` runs it best-effort (a live cluster is not a container-start precondition). The block is the script's own — it never edits lines outside the fence, and re-runs converge on the current Gateway IP.                                                                                                                                                                                                                                                                                                                                                                                 |

## Java origin

No Java twin: this is Aurelius test infrastructure (the e2e suites are
Aurelius-side, ADR 051's parity harness consumes them; Apache Atlas tests
against an embedded JanusGraph stack and has no deployment axis).

## Deviations

None new. The aux audience overlay is environment configuration, not a
behavioural deviation — the shipped charts and DV-74/DV-75's shapes are
untouched.

## Acceptance

Unit (library, no cluster):

- `libs/python/aurelius-atlas-cluster-lane/tests/` — the gate's fail-fast
  message naming `install.sh up`, the shim's bytes/str host matching, its
  host-only registration for a forward and its (host, port) pair shape for
  callers that need a port moved, `SecretReader`'s decoding,
  `ServiceForward`'s free-port command shape, the hosts-file fence edit (tmp
  file, both first-insert and converge-on-churn paths). All marked
  `@pytest.mark.covers(..., rules=["CHT-103", "CHT-104", "CHT-106"])` on the
  named functions (ADR 056).

Chart (rendered, no cluster):

- `tests/test__charts_aux.py` — new: the minikube overlay render carries both
  aux `AUTH_AUDIENCE=aurelius` envs (CHT-105) while the default render keeps
  the per-service audiences.

E2E compose lane (the regression bar — every suite byte-identical):

- `nx e2e aurelius-atlas-server` (37), `-data2model` (7), `-validate-entity`
  (7), `pytest libs/python/aurelius-atlas-core/e2e` (23) green unchanged.

E2E cluster lane (local, `tools/cluster/install.sh up` as precondition):

- `nx e2e-cluster` on the same four projects, green cold (fresh `up`) and
  warm (rerun), against the same release — the twins' five/ten assertions
  unchanged, the core suite riding the shared store, the server suite
  unchanged through the refactored conftest (the extraction's honesty check).
- Negative: `ATLAS_E2E_TARGET=cluster` against a down release fails at the
  gate within seconds, naming `install.sh up` (CHT-53/103's fail-fast stays
  through the library).
- Hosts: `install.sh hosts` against a live cluster writes the fenced block
  with the live Gateway IP; re-running after an IP change replaces it and
  touches nothing outside the fence (CHT-106).

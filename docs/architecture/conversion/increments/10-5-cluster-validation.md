# 10.5 Cluster validation (POC): install script + the server suite on the cluster

- **Status:** in progress
- **Pull request:** #187 (stacked on the 10.11 line, #186)
- **Records:** DD-280 (adds), DD-252 (relies on: the stuck-release recovery the
  script scripts), DD-265 (relies on: the split-horizon CoreDNS patch the
  script applies), DD-251 (relies on: the trial install whose lessons the
  script encodes), DD-247 (relies on: the chart-target plugin — the new
  target is hand-written, and named to stay outside it), DD-261/270 (relies
  on: the edge the POC lane finally drives)

## Scope

The motivation is the legacy chart's disease: charts nobody could trust
because nothing ran them. The cure is the deployment _being_ the test
environment, so this increment rewires one project's real e2e suite to run
against the Helm umbrella instead of docker compose, as a **local POC**.

- **The install script** (`tools/cluster/install.sh`, CHT-50/51/52): runbook
  §0–2 as code — minikube lifecycle, cert-manager, Envoy Gateway plus the
  GatewayClass EG ships none of, the DD-265 CoreDNS split-horizon patch, the
  image build-and-load pass (no pull secrets on minikube), and the umbrella
  install with the DD-252 stuck-release recovery scripted. Idempotent: every
  subcommand is safe to re-run against a live cluster.
- **The POC lane** (CHT-53..56): `apps/aurelius-atlas-server/e2e` grows an
  opt-in deployment axis — `ATLAS_E2E_TARGET=cluster` (via a new hand-written
  `e2e-cluster` Nx target) drives the **unchanged tests** through the
  installed umbrella: the Gateway edge, the webapp nginx `/api/` proxy,
  backend TLS, and a port-forward only where the cluster publishes nothing
  (Tempo's query API, the server's baked dashboard). The default lane is
  untouched compose.

This POC explicitly does **not** deliver: CI integration (no workflow runs
either lane differently — that decision is what the POC exists to inform);
webapp/aux-API rewiring (rollout increments, per suite, after the verdict);
retiring any compose stack (they stay the working reference the POC compares
against); auth'd traffic (server auth is H1's, unchanged); prod-realm runs
(the install script's `--realm` flag exists, but the POC exercises `master`).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CHT-50 | `tools/cluster/install.sh` is the only supported cluster-install path: `up` / `status` / `down` (+ `images` as `up`'s step), each idempotent, flags for domain/realm/cluster sizing, `helm dep update helm` always before the install, and no blind `--atomic`: a release found in a `pending-*` state is uninstalled (waited) and reinstalled per DD-252.                                                                                                                                                                                                                                                               |
| CHT-51 | `up` converges the runbook §0 prereqs before touching the umbrella: cluster running (4 CPU/8 Gi defaults), `atlas` namespace, cert-manager ready, Envoy Gateway installed **and** the hand-made `envoy-gateway` GatewayClass, the CoreDNS `rewrite stop name keycloak.<domain> → atlas-keycloak.atlas.svc.cluster.local` patch (line-based, Corefile-flavour-agnostic) with a coredns roll, and `minikube tunnel` backgrounded with a pidfile.                                                                                                                                                                           |
| CHT-52 | Images ride the cluster, not a registry: `up` builds the six Aurelius images at `:latest` (the chart's appVersion default) and loads every image into minikube (the authoritative list read from a stock render of the minikube overlay); `imagePullPolicy: IfNotPresent` makes pull secrets unnecessary. A digest pin cannot be loaded by digest — `minikube image load` of a `repo@sha256:…` reference is a silent no-op — so each pin travels under the tag its chart declares beside the digest (CHT-93) and the exact digest name is re-applied in the node's containerd. `--skip-build` consumes pre-built images. |
| CHT-53 | The suite's lane is env-gated: `ATLAS_E2E_TARGET` selects `compose` (default — every existing invocation, CI included, is byte-identical) or `cluster`; the `e2e-cluster` target exists only to set it, is named outside the Python plugin's inference so nothing references it, and `cache: false` (a live cluster never replays).                                                                                                                                                                                                                                                                                      |
| CHT-54 | Cluster mode gates and dials honestly: the `atlas` release must answer `deployed` (fail-fast naming `install.sh up`, never a silent skip); the suite resolves `*.atlas.test` to the Gateway's address through a process-local `socket.getaddrinfo` shim (no /etc/hosts), so requests carry the real hostname through HTTPRoute match, SNI, and verified SANs, and `server` yields `https://atlas.atlas.test` — traffic rides Gateway → webapp nginx → server, the whole deployment.                                                                                                                                      |
| CHT-55 | Cluster-only surfaces get local ingress, not exposure: Tempo's query API (port-forward to `svc/atlas-observability-tempo:3200`) and the server's baked legacy dashboard (port-forward to `svc/atlas-server:21000` — the edge's `/` belongs to the SPA) reach the suite through fixtures; the cluster publishes nothing new to the host.                                                                                                                                                                                                                                                                                  |
| CHT-56 | The trust follows the lane: compose verifies against the mkcert dev CA (`nx certgen`); cluster mode pulls the chart's `aurelius-atlas-selfsigned-ca` Secret and verifies the edge leaf against it — certificate validation is never relaxed on either lane.                                                                                                                                                                                                                                                                                                                                                              |

## Java origin

None — this increment ports no Apache Atlas behaviour. Its subject is this
project's own deployment surface; the reference is the runbook sequence and
the hand-check findings from the 10.2/10.3/10.6 design-log entries.

## Deviations

None against Atlas. Against our own increment rules, recorded honestly (DD-280):

- **No CI gate yet.** The convention is every increment lands behind CI; this
  one deliberately stops at local runs — the user's decision, because the
  POC's question (can the deployment host the suites at all, and what does it
  cost: image loads, boot time, limiter behaviour, edge fidelity) is
  answered locally, and wiring CI before the answer risks a permanently
  expensive or flaky job. The rollout increment carries the CI design.
- **Dual-mode instead of replace.** A rollout would delete the compose lane;
  a POC must keep it as the reference the cluster lane is compared against.
- **minikube, not KinD** (carried from the earlier plan): the runbook, the
  overlay, and every hand-check note say minikube; a second flavour is drift.

## POC verdict — acceptance-run findings

The acceptance run passed on both lanes (37 green compose, 37 green cluster,
warm re-run green, fail-fast negative green). Three findings it surfaced,
each fixed in this increment:

- **A digest pin cannot be loaded by digest** (CHT-52 rewritten): minikube's
  image-load silently skips `repo@sha256:…` references, so the digest-pinned
  infra images never landed and their pods sat in `ErrImagePull`. Pins now
  travel under the chart-declared tag (parsed from the values beside each
  digest, CHT-93) and `ctr images tag` re-applies the digest name inside the
  node — the honest direction, since `docker tag <digest> <tag>` names the
  verified bytes, never the reverse.
- **The parity scenarios assert a tasks-disabled install** (DD-081): the
  compose e2e stack has always pinned `TASKS_ENABLED=false`, the charts never
  did, so the cluster answered `/session` with `atlas.tasks.enabled=true` and
  five scenarios failed — one real expectation diff, four classification
  timeouts behind it. The minikube overlay now carries the same pin
  (environment = values, CHT-04). This is exactly the drift class the POC
  exists to catch.
- **httpcore resolves as bytes**: the DNS shim must match both `bytes` and
  `str` hosts — an `isinstance(host, str)` shim is transparently bypassed by
  httpx's resolver (CHT-54's shim covers both forms).

## Acceptance

- `uv run pytest apps/aurelius-atlas-server/e2e` (compose lane, default env)
  — 37 tests green, unchanged from before the rewire: the POC moved nothing.
- `tools/cluster/install.sh up` on a fresh cluster (`minikube delete` first)
  → `ATLAS_E2E_TARGET=cluster uv run pytest apps/aurelius-atlas-server/e2e`
  → 37 green through the edge (the POC's verdict line).
- Re-run green against the warm cluster (reuse); `install.sh up` re-run
  converges as a no-op (CHT-50 idempotency); `helm uninstall atlas -n atlas`
  then cluster-mode pytest fails fast with the install.sh pointer (CHT-54's
  fail-loud).
- `uv run pytest tests/` and `npx nx run-many -t helm-lint helm-template`
  unchanged; `nx show project aurelius-atlas-server --json` shows the
  inferred compose `e2e` and the hand-written `e2e-cluster` side by side.
- `git diff` review confirms zero changes to `.github/workflows/`, any
  `dev/*` stack, or any other project's suite.
- The rule ids above name the artifacts; the suite's existing `covers`
  markers are untouched (the POC adds behaviour, not rules to the Atlas
  semantics — CHT-50..56 ride the script and conftest as reviewed-as-code,
  the CHT-95 precedent).

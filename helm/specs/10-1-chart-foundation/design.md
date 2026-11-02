# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-283. One chart per component under an umbrella, published as OCI artifacts

- **Status:** Superseded by DD-290 (the `charts/` residence; one-chart-per-
  component, umbrella, and OCI publish stand)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Deployment lives in a top-level `charts/` tree: one chart per
deployable component (`atlas-server`, `atlas-webapp`, `atlas-data2model`,
`atlas-lineage-model`, `atlas-validate-entity`, `atlas-elasticsearch`,
`atlas-keycloak`, `atlas-observability`), a Helm library chart `atlas-common`
for the shared helpers, and the umbrella `aurelius-atlas` that composes them.
A component chart owns its component's runtime contract (port, probes,
`AURELIUS_ATLAS_*` settings, trust mounts); the umbrella owns the edge, the
trust issuers, the shared secrets, and the `global.*` values contract. Charts
publish to `oci://ghcr.io/aureliusenterprise/charts` in the release.

**Reason.** ADR 057. The increment that changes a component is the one that
knows its ports and probes, so ownership sits at the component (R3); the
combination that CI proves is one install of the umbrella (R4); a registry
artifact under the release's number, in the registry the images use, with the
credentials CI already has, is the smallest addition to the delivery plane
(R7). `charts/` as one tree keeps chart-to-chart edges — the common library,
the umbrella's pins — visible in one place, and each project's `AGENTS.md`
points at its chart.

**Alternatives.** (a) `apps/<app>/chart/` — one step more local, and it
interleaves the docker plugin's `**/Dockerfile` glob with a `**/Chart.yaml`
glob in the same directories; the deployable unit is a chart, and the app tree
is organised by conversion increment, not by deployment. (b) One monolithic
chart — R3's failure, the file where component knowledge goes stale.
(c) Charts in their own repositories — R2's failure, and ADR 001's; a
component change and its chart change stop being one commit. (d) Kustomize —
no chart artifact to publish (R7) and env-var text substitution where the
components need typed, validated values.

**Consequences:** `charts/AGENTS.md` carries the chart conventions the way
`libs/python/AGENTS.md` carries the library recipes. The example apps get no
chart — they leave with 6.4 (DD-019). The dashboard is not a chart: it is
copied into the server image (`/application/dashboard`, DD-018). Publishing
order becomes load-bearing (subcharts before the umbrella, DD-288). Next free
DD: 241.

### DD-284. Helm targets are inferred from `Chart.yaml` by a plugin mirroring `docker.ts`

- **Status:** Superseded by DD-293 (the inference and the plugin stand; the
  separate `<chart>-chart` PROJECT does not — targets merge onto the owner)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** `tools/plugins/helm.ts` infers, for every `charts/**/Chart.yaml`,
an Nx project named `<chart>-chart` (tagged `helm`) with `helm-lint`,
`helm-template` (`local`/`ci` configurations) and `helm-publish`
(`--namespace oci://ghcr.io/aureliusenterprise/charts`, `version` default
`local`, publish `latest`, CI passes `--version $VERSION`) — the option,
configuration, and metadata shape of `tools/plugins/docker.ts`.

**Reason.** ADR 021 (a technology joins by recipe: discovered, gated,
releasable, removable in one pass) and DD-283's R7. Inference makes charts
graph-visible, so `nx affected -t helm-lint` gates a chart change and
`nx run-many -t helm-publish` releases them — the same two commands that
already carry images. The docker plugin is the house pattern; a second shape
for the same job costs review attention.

**Alternatives.** (a) One root `helm` project looping charts in a shell script
— invisible to `affected`, no per-chart cache, no per-chart target to compose.
(b) A `project.json` in each chart — nine manifests to keep in step, where one
plugin file infers all nine. (c) `@nx/kubernetes` — it generates kustomize
scaffolding, not Helm targets.

**Consequences.** The validate job adds `nx affected -t helm-lint helm-template`
(level 0: no cluster, no registry, no SOPS key — helm 4.3.1 is in the dev
container, which is the CI runner image, so nothing installs). Release
grouping picks chart projects into the version plan (DD-288). The plugin's
commands are helm 4 flags; a helm 3 operator can lint the charts but the
publish path assumes helm 4's OCI push. Next free DD: 242.

### DD-285. The edge is Gateway API, not ingress-nginx

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The umbrella renders the edge as Gateway API resources: one
`Gateway` and one `HTTPRoute` per host (`atlas.<domain>` → webapp,
`keycloak.<domain>` → Keycloak, optional dashboard and Grafana hosts), with
`gateway.className` a value (Envoy Gateway on minikube, the provider's
implementation on a managed cluster). No ingress-nginx, no ingress-level
instrumentation, no service mesh.

**Reason.** ingress-nginx retires in March 2026 — best-effort maintenance
until then, no security fixes after (kubernetes.io, 2025-11-11) — so building
the deployment on it starts a migration on day one. Gateway API is the
successor and is the portable choice by construction: the chart names an API,
the cluster names an implementation, which is R1 in one line. The policy the
edge used to be chosen for already lives one hop in: the webapp's nginx owns
the browser rate limit (DD-238) and the `/api/` tracing export (DD-239), and
it is tested by the e2e suites.

**Alternatives.** (a) ingress-nginx — retired; its snippet annotations are the
security debt the retirement names. (b) Traefik, Kong, Moov — capable, and
each makes its own CRDs and policy vocabulary a chart dependency, so
portability costs a value per controller; as a GatewayClass implementation
each is a value swap. (c) LoadBalancer Services only — two browser-reachable
hosts (webapp, Keycloak) on one address needs host routing. (d) Istio —
a mesh sidecar model replaces the pinned-CA trust the components ship with
(ADR 039, DD-234) and adds a data plane to operate for a policy set already
implemented in nginx.

**Consequences.** A GatewayClass is a cluster prerequisite, installed by the
install script and named in the runbook (10.4). TLS terminates at the gateway
and the webapp→server hop stays TLS (DD-286's per-service certificates).
Routing stays coarse: one host to one service, because the webapp's `/api/`
and `/otel/` proxy is the tested data path (DD-142) — the gateway does not
duplicate it. Next free DD: 243.

### DD-286. TLS trust is cert-manager issuers; each pinned CA is a ConfigMap of the trust root

- **Status:** Accepted (the default issuer's shape superseded by
  [DD-259](../10-2-stateful-platform/design.md#dd-259-the-chart-managed-trust-root-is-a-namespaced-self-signed-issuer-chain))
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The umbrella owns the trust model: an issuer reference
(`global.issuerRef`, a self-signed `ClusterIssuer` by default, swappable for
ACME, a provider CA, or an existing chain) and one `Certificate` per
browser host and per in-cluster service, with the SAN sets the consumers
verify (service DNS names for internal hops, the host names for the edge).
The CA every consumer pins by file — `ELASTICSEARCH_CA_CERTS`, nginx
`proxy_ssl_trusted_certificate`, `AUTH_CA_FILE`, `OTEL_*_CA_FILE`, the store's
`tls/ca.pem` — is supplied as a ConfigMap of the issuer's CA, mounted at the
path the chart names, through a helper in `atlas-common`.

**Reason.** ADR 039 declares TLS at every hop and the components enforce it:
the server refuses to start without key, cert, and CA (SRV-06, DD-234), and
nginx, Keycloak, Elasticsearch, and the collector each pin a CA file. So the
chart must deliver files, not secrets alone. cert-manager is the one mechanism
that produces a leaf and its `ca.crt` on every cluster, minikube included
(R1, R6), with rotation built in. The dev CA cannot travel: `tools/tls/certgen.sh`
is mkcert-root based, mode-644 keys, and its header forbids shipping `certs/`.

**Alternatives.** (a) Bring-your-own TLS secrets — the chart stays dumb and
every environment hand-produces eight leaf certificates with eight SAN sets and
renews them by hand; R6's failure is that no test catches a wrong SAN.
(b) SPIFFE or mesh-issued identities — a third identity system beside Keycloak
and the `otel-*` client credentials (ADR 007, ADR 013). (c) Plaintext in-cluster
hop-by-hop — refused by ADR 039: a declared arrangement, not an assumed property.

**Consequences.** cert-manager is a prerequisite of every cluster (install
script, runbook). Consumers that read the CA at boot (Elasticsearch, Keycloak)
need a restart hook when the CA rotates — recorded for 10.2/10.3. A private
root is the default, so the cluster's trust set is closed and enumerable;
swapping `issuerRef` to ACME changes the browser certificates only, because
internal consumers pin the internal issuer's CA. Next free DD: 244.

### DD-287. The umbrella owns shared secrets, generated at install and preserved on upgrade

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Every credential the system needs at runtime is produced by one
umbrella template from one `secrets.*` values block and written as plain
`Secret`s, one per consumer: the store's `elastic` password, Keycloak's
bootstrap admin and database credentials, the `otel-*` client secret the realm
shares, the two demo users, and the collector's legacy-leg token. A value
supplied in values wins; a value absent is generated (`randAlphaNum`) and
**preserved across upgrades** by reading the live Secret (`lookup`) before
generating. The webapp's ingest token is the legacy-leg token, documented as
browser-reachable — a public ingest endpoint's constant, not a confidential
credential.

**Reason.** R5 (no secret in the artifact) and R6 (a fresh minikube install
with no prepared secrets must reach a running system). The preserve step is
not decoration: regenerating the store's password on upgrade bricks the system
of record, and the first install of a generated secret is the only moment the
value exists. That the browser leg's token is public follows from DD-239 — the
edge exports on the legacy leg from the browser's request path, so the value
travels where an attacker with a page load can read it; the honest model is an
OTLP ingest DSN, and the audit trail is the OIDC legs (7.17/7.18).

**Alternatives.** (a) The repo's SOPS `.env.enc` — those files are per-project
dev defaults readable by every developer's age key (ADR 008); production
credentials in them inherit that audience. (b) External Secrets Operator or a
cloud secret manager — the right answer for a deployment that runs one, so the
chart consumes plain `Secret` names and leaves the door open (option in the
runbook, 10.4) rather than binding the chart to a backend. (c) helm-secrets /
sops in the operator's path — adds a CLI and an age-key distribution problem
to the install.

**Consequences.** `helm uninstall` deletes the credentials, so the runbook
names the backup duty with ADR 026/028 and the rotation procedure (10.4);
retrieval is `kubectl get secret -o jsonpath`. Talisman and pre-commit see no
secrets because none are committed. A deployment that wants per-environment
secrets in its own store sets them in values and gets the same preservation.
Next free DD: 245.

### DD-288. The umbrella pins its component charts to its own version; chart version equals release version

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Every chart's `version` is the release's semver and its
`appVersion` the image tag. The umbrella's `dependencies` pin each component
chart to `=` its own version and resolve them from the OCI repository, so
`helm install aurelius-atlas` on a deployment's machine pulls exactly the set
CI tested. `publish.yaml` publishes subcharts before the umbrella.

**Reason.** ADR 019's one number must name a shippable combination, and CHT-07
is the chart half of that promise: a range (`>=1.2.0`) resolves to "the newest
of each", which is a combination no pipeline ever ran. Pin-equal makes mixing
impossible and makes the release the unit of deployment, the same argument
that gives the images one tag.

**Alternatives.** (a) Caret/range pins — the drift generator this decision
exists to refuse. (b) `file://` dependencies only — the umbrella would carry
tarballs and a component chart could not be installed standalone from the
registry (a deployment standing up Keycloak alone for a staging test).
(c) Independent chart versioning — a chart fix ships without a release, so
"the release" stops naming what runs; R2's failure, and the one ADR 019
forbids.

**Consequences.** Charts join the release group, so Nx release bumps them with
the rest (DD-284); a chart-only fix costs a release — the deliberate price of
R2, and the same price the images already pay. Development installs can use
the local tree (umbrella `file://` dependencies behind a values switch) so
chart hacking needs no publish; publish ordering is subcharts → umbrella,
checked by the verify step 10.4 adds. Next free DD: 246.

### DD-289. The chart gate renders each chart's own values files; the release refreshes Chart.lock

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** `helm-template` renders a chart once per values file it ships —
`tests/values.test.yaml` and each `environments/*.yaml` overlay — as separate
`helm template` invocations, never as one stacked command. The chart
projects' `afterAllProjectsVersioned` refreshes the umbrella's `Chart.lock`
with `helm dep update` after a release writes the new versions.

**Reason.** Stacked (`-f a.yaml -f b.yaml`) renders only the umbrella's
combination; a component chart's own overlay pair (test values + environment)
is a combination no deployment runs, and stacking every chart's files in one
command hides which file breaks. Separate renders name the failing file. The
lock refresh exists because `Chart.lock` records the resolved dependency
versions and a digest over them: a release that bumps the component charts
leaves it stale, and only helm computes the digest — the tree is flushed to
disk by the time the hook runs, so `helm dep update` is the only writer that
can produce a valid lock.

**Alternatives.** (a) One stacked render — fails the naming-the-file goal and
makes a component chart's CI green without its own contract ever rendering.
(b) Gitignore `Chart.lock` — helm's own contract wants the lock committed
(`helm dep build` verifies against it); an unlocked install resolves
dependencies at install time, which is DD-288's drift generator re-opened.
(c) A `helm-lock` Nx target — a release-time action, not a developer one; the
version-actions hook fires exactly when the lock goes stale.

**Consequences.** The gate's task count grows with the values files a chart
ships (20 tasks for 11 charts today); every chart that gains an overlay gains
a render. The lock refresh runs in `nx release version` only (a dry run
skips it, and the `--dry-run` flag's tree is empty), so the version commit
carries a valid lock. The plugin's target command is generated at graph-build
time from the files on disk — adding an overlay changes the task's command,
which is a cache miss. Next free DD: 247.

### DD-290. Component charts live next to their projects; helpers are chart-local

- **Status:** Accepted (supersedes DD-283's `charts/` residence; its
  one-chart-per-component split, the umbrella, and the OCI publish stand;
  the umbrella's `charts/` residence is superseded by DD-292)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Each component chart lives in a `helm/` directory inside the
project it deploys — `apps/<app>/helm/` for the five apps,
`dev/<name>/helm/` for the three infrastructure components. `charts/` keeps
the umbrella `aurelius-atlas` only: it is the one chart with no owning
project. The two library charts (`atlas-common`, `atlas-aux-api`) are
deleted: their helpers are expanded into each chart's own
`templates/_helpers.tpl` and template files, keeping the naming convention
(`<chart>.fullname`, `<chart>.labels`, …). The umbrella reaches its
components through `file://../../apps/…/helm` dependencies; names, pins
(CHT-07), and OCI artifacts are unchanged.

**Reason.** The chart's owner is the project's owner: a change to a
component's ports, settings env, or probes rides the same PR as the code it
deploys, and the PR's diff shows the blast radius (workload + chart) in one
place. A library chart is a component with no runtime — nothing runs it,
nothing deploys it, and every consumer sits in the same repo — the
artificial-abstraction shape this workspace's module rule rejects. 10.1's
gate measured the shared surface as small (mostly `required:` guards), so
the copies are cheap; DD-283's "chart-to-chart edges in one place" is the
umbrella's `Chart.yaml` (the single join) plus the naming convention. The
Nx plugin infers targets from a `**/Chart.yaml` glob, so the move is a
tooling non-event — zero plugin changes.

**Alternatives.** (a) Keep the `charts/` tree (DD-283) — the ownership map
lives only in docs, and contributors must know to visit a sibling tree.
(b) Keep `atlas-common` as the only library — the shared helpers stay
shared, at the cost of every chart depending on a project that runs
nothing; the convention dedupes what a library would share.
(c) Name the directory `chart/` — `helm/` is unambiguous (the Helm
convention, parallel to `docker/`-style folders) and reads as the deploy
toolchain of the project.

**Consequences.** Each owning project's `AGENTS.md` documents its chart
(layout bullet + a Helm-chart section); `charts/AGENTS.md` covers the
umbrella and the shared conventions/gotchas. Component charts are
dependency-free, so their `Chart.lock` files are gone; the umbrella's lock
regenerates with 8 entries. The prettier/check-yaml template excludes and
the gitignore dependency-tarball rules widen from `charts/*/…` to
`**/helm/…`. The gate keeps its task count (the libraries contributed two
lint tasks). The aux-API deployment/service shape now exists three times
(verified byte-identical at the copy); the three charts may drift on
purpose — the convention, not code, is the dedupe. Next free DD: 248.

### DD-291. The Chart.yaml is the chart's whole Nx identity; no chart project.json

- **Status:** Superseded by DD-293 (the no-`project.json` rule and the
  everything-from-`Chart.yaml` rule stand; the separate `<chart>-chart` PROJECT
  — the plugin's `name` field — does not)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** A chart ships no `project.json`. The helm plugin reads
everything it needs from `Chart.yaml` itself: the project **name**
(`<chart>-chart`, from the `name:` field — the same name Helm gives the
packaged artifact), `projectType: application`, the `helm` tag, the release
`versionActions`, and — for the umbrella — the `implicitDependencies` that
drive `helm-publish`'s cascade, derived from the `dependencies:` block.
DD-284's inference claim becomes literally true: the chart directory is
`Chart.yaml`, `values.yaml`, `templates/`, `tests/`, and nothing else.

**Reason.** The `project.json` files existed only to carry four fields the
plugin could derive, and each was a second statement of a fact `Chart.yaml`
already states: the chart name (`name:` = the artifact name = the project
name base), the dependency edges (the umbrella's `dependencies:` = the
cascade graph = the CHT-07 pins). Two sources of one fact is the drift the
conversion workflow bans. The naming suffix is load-bearing, not cosmetic:
without it, nine folders all named `helm` would derive colliding project
names, and the release's pin lookup (`<project>-chart → chart name`) needs
the mapping — deriving it from `Chart.yaml name:` keeps chart and project
names equal by construction.

**Alternatives.** (a) Keep the nine `project.json` files — nine manifests
echoing facts the manifest of record already carries (DD-284's own
rejected alternative (b)). (b) Folder-derived project names
(`apps-aurelius-atlas-server-helm`) — stable but verbose, collides on plain
`helm` folders, and breaks the `<chart>-chart` naming the CI invocations,
docs, and the release pin lookup use. (c) Name the projects from the
owning app (`aurelius-atlas-server`) — the chart is a distinct artifact
with its own version and OCI repository; the `-chart` suffix keeps the
image project and the chart project addressable apart.

**Consequences.** Adding a chart is files only: `Chart.yaml` + values +
templates + test values (+ the umbrella's dependency row) — nothing to
register. Removing a slice removes one file fewer. The plugin gained two
small line-parsers (`name:`, `dependencies[].name`) in
chart-yaml-version-actions.ts's no-YAML-library style; the umbrella's
dependency list is now load-bearing for the publish cascade as well as for
install. Next free DD: 249.

### DD-292. The umbrella sits at the workspace root: `helm/`

- **Status:** Accepted (supersedes DD-290's clause that the umbrella is the
  only resident of `charts/`; the component-chart placement and the
  no-library-charts rule stand, and DD-283 is superseded the same way)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The umbrella chart `aurelius-atlas` lives in `helm/` at the
workspace root; the `charts/` directory is gone. The chart tree is now one
shape: every chart in the repo is a `helm/` directory — the component charts
next to their projects (DD-290), the umbrella at the root. The umbrella's
`file://` dependencies shorten one level (`file://../apps/<app>/helm`), and
its lock is `helm/Chart.lock`.

**Reason.** DD-290 moved every component chart to its owner; the umbrella
has no owning project — it deploys the whole system — so its place is the
root. It also completes the naming convention: the chart is the Helm
toolchain of "the workspace project", exactly as `apps/<app>/helm/` is of
an app. A single-chart directory named `charts/` (plural, one entry) was a
vestige of the tree DD-290 dismantled.

**Alternatives.** (a) Keep `charts/aurelius-atlas/` — DD-290's rationale
applied verbatim: an owning scope exists (the workspace), the folder is
just `helm/` at root, and the residual `charts/` tree exists only for the
umbrella. (b) `helm/aurelius-atlas/` (chart name inside the root dir) —
one directory deeper than needed; a chart directory is one chart, and
`helm/` at root already says whose.

**Consequences.** The plugin needs zero changes (the `**/Chart.yaml` glob
finds the root chart; the Nx project root becomes `helm`). The release
lock-refresh hook targets `helm/Chart.lock`. The prettier/check-yaml/
gitignore patterns converge on `**/helm/{templates,charts}/` — the
`charts/aurelius-atlas/...` special cases are deleted, not widened. The
`.helmignore-shared` template moves to `helm/.helmignore-shared`. Next
free DD: 250.

### DD-293. Helm targets merge onto the owning project: a chart is not a project

- **Status:** Accepted (supersedes DD-284 and DD-291: the plugin's inference
  and the no-`project.json` rule stand, the separate `<chart>-chart` projects
  do not)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The helm plugin keys its `createNodes` result at the chart's
OWNER root — the chart dir's parent (`apps/<app>/helm` → `apps/<app>`; the
root `helm` → `.`) — so Nx shallow-merges `helm-lint`/`helm-template`/
`helm-publish` and the `helm` tag onto the existing project node. No `*-chart`
project exists. The plugin sets no `name` (a node's name belongs to the first
plugin that claims its root, helm runs before the ecosystem plugins, and
naming here would rename the owner) and no `projectType`. The umbrella's
dependency edges become `implicitDependencies` on the OWNING projects,
resolved by following each `dependencies[]` `repository: file://` path to the
chart dir and reading the owner's name (project.json, pyproject.toml,
package.json). Release: every chart owner points `release.version.versionActions`
at the composite module (`tools/plugins/chart-yaml-version-actions.ts`), which
versions the owner's ecosystem manifest AND its `helm/Chart.yaml`, re-pins the
umbrella (dependency entries are looked up through the owner name), and
refreshes `helm/Chart.lock` — wired from `python.ts` for the uv projects
(which overwrites the plugin's same-valued field), from `project.json` for the
dev charts, from the plugin at the root project.

**Reason.** The nine `*-chart` projects were graph noise: one chart per
project already (DD-290), so the chart project and the app project share a
root, a release bump, a CI run, and an owner. A chart change touched two graph
nodes; `nx affected -t helm-lint` listed a project no one navigates to, and
each app's target list carried `helm-*` beside its own `build`/`test` under a
name no one types. Merging by parent root is Nx's documented merge (a
same-root inference result adds targets to the existing node), the
project.json-override layer is untouched, and CI is target-based (`affected
-t helm-lint helm-template`, `run-many -t helm-publish`) so it sees no change.
The chart tree, the CHT rules, the pin-equal release (DD-288), and the OCI
artifact are untouched — only the graph shape.

**Alternatives.** (a) Keep the chart projects (DD-284/DD-291) — a stable name
per artifact, addressable apart from the image; paid in graph noise and split
`affected` output. (b) Folder-derived owner names — not available: `name` is
first-plugin-wins, helm runs early, and the plugin has no project-name map in
the v1 context; the parent's name comes from its own manifests, read the same
way the release's pin lookup reads them. (c) Keep the chart projects and alias
them in `nx.json` — an artificial abstraction the tree rejects (DD-290).

**Consequences.** Release needed a composite: chart version writes, umbrella
pin refresh, and the lock hook all lived on the chart projects' version-actions
and now run on the owners' — the composite extends `@nxlv/python`'s actions for
pyproject owners, treats `Chart.yaml` as the manifest for chart-only owners,
and maps umbrella pins by owner name through the `repository:` paths (the
dependency parser reads entries, not line-adjacent pairs, so a `repository:`
after `version:` resolves). The `-chart` suffix and its pin-lookup convention
are gone — the chart name lives only in `Chart.yaml`/`repository:`. `npx nx
show project aurelius-atlas-server` lists the chart targets. The release
dry-run keeps its shape: 9 Chart.yaml writes + 8 umbrella pin updates. Docs'
per-chart commands become `npx nx run <owner>:helm-template`. The dev charts'
`project.json` swap noop actions for the composite (their chart is their
version manifest). Next free DD: 251.

### DD-298. A stuck pending-install release is cleared by uninstall

- **Status:** Accepted
- **Increment:** 10.1 (trial)
- **Date:** 2026-10-28

**Decision.** The runbook's install/upgrade sections warn: `helm install
--wait` (or `--atomic`) against a workload that never reaches Ready — a
crash-loop, a missing Secret — burns the full `--timeout` and leaves the
release `pending-install`; every later `helm upgrade` then fails with
"another operation (install/upgrade/rollback) is in progress" until `helm
uninstall` clears it. Fix the cause, inspect with `helm history`, and
uninstall rather than waiting the release out.

**Reason.** Observed twice in the trial of DD-294: the first install timed out
on the crash-looping aux pods and the stuck release blocked the fix-and-retry
path with a confusing error unrelated to the actual defect. It is helm's
documented behaviour, not a chart bug, so it belongs in the runbook, and
mid-roadmap installs (subcharts that render no workloads yet, workloads whose
wiring lands in a later increment) are exactly when an operator meets it.

**Consequences.** The runbook gains the note and the `helm history` /
`helm uninstall` recovery lines; 10.5's install script scripts the recovery
(guard the wait with a pre-flight, or clean up on timeout) rather than
discovering it again. Next free DD: 253.

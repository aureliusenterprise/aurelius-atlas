# helm/

The umbrella chart of the system (ADR 057), at the **workspace root**: the
umbrella deploys the whole system, so it sits next to the whole repo
(DD-249). Component charts live **next to the project they deploy** —
`apps/<app>/helm/`, `dev/<name>/helm/` (DD-247). Every chart in the tree is
a `helm/` directory; `charts/` is gone. Workspace-wide rules, including the
conversion workflow, live in the root `AGENTS.md`. Increment 10.1 is the
foundation (charts, plugin, CI); 10.2 landed the stateful charts
(elasticsearch, keycloak); 10.3a lands the app charts (server, webapp, the
three aux APIs) and the umbrella's Gateway-API edge; 10.3b is the
observability workloads; 10.4 secrets + publish; 10.5 cluster validation;
10.6 network segmentation.

## Layout

- `helm/` (this directory) — the umbrella `aurelius-atlas`: the edge
  (Gateway + HTTPRoutes), the trust issuers, the generated secrets, and the
  `global.*` contract (CHT-03). Its `environments/{minikube,gke}.yaml` are
  the tested environment overlays (CHT-04 — environment = values, never a
  chart fork).
- Component charts (the map; each project's `AGENTS.md` covers its own):
  `atlas-server` + `atlas-webapp` in `apps/aurelius-atlas-{server,webapp}/helm`,
  the three aux APIs in `apps/aurelius-atlas-{data2model,lineage-model,validate-entity}/helm`,
  `atlas-elasticsearch` in `dev/elasticsearch/helm`, `atlas-keycloak` in
  `dev/keycloak/helm`, `atlas-observability` in `dev/observability/helm`.
- Every chart ships `tests/values.test.yaml` (its CHT-06 render inputs) and a
  `Chart.yaml` whose `version:`/`appVersion:` are release-managed (DD-245,
  `tools/plugins/chart-yaml-version-actions.ts`). A chart is **not a project**
  (DD-250): the plugin infers its targets onto the OWNING project (the chart
  dir's parent — the root project for the umbrella), keyed at the owner's
  root, and wires the composite release module there. The umbrella's
  `dependencies:` block doubles as its implicitDependencies on the owning
  projects (chart → `repository:` path → owner). No `*-chart` projects, no
  per-chart `project.json`.

## The values contract

Each chart declares the FULL `global.*` shape in its own `values.yaml` with
empty defaults, so it renders standalone; through the umbrella, Helm's
`global` merge passes the umbrella's values down, and the umbrella is the
source of truth. Deep access into a missing value map panics the Go template
(nil pointer) — a chart that reads `global.x.y` must ship the whole shape.
The contract: `namespace`, `labels`, `image{registry,namespace,tag,pullSecrets}`,
`storageClass`, `domain`, `realm` (CHT-74: the Keycloak realm every issuer URL
names and the Keycloak chart imports `files/<realm>.json` from — default
`aurelius-atlas`, first-boot-immutable like the issuer; `master` is the dev
escape hatch, DD-273; the KC chart additionally declares `hosts.{atlas,
dashboard}.host` for the realm asset's browser-host substitution, CHT-77),
`issuer.url`, `dnsResolver`, and
`trust.issuerRef` (`{name, kind}` — the issuer every component `Certificate`
signs against; with `trust.createIssuer` on (the default) the umbrella
renders the chain itself — bootstrap self-signed `Issuer` → `isCA` root
`Certificate` → `ca` `Issuer` — all namespaced, because a `ClusterIssuer`
cannot read a CA Secret in the app namespace (DD-259); off means the
operator brings their own issuer).

Names: a release prefixes its charts (`<release>-<chart>`); the fullname
helper drops the prefix when the release name already starts with it, so the
release `atlas` keeps names bare (`atlas-server`) and service DNS matches
what the components' settings reference.

## The edge (CHT-29..32)

`global.gateway.enabled` (default on) renders: one `Gateway` named after the
release, one HTTPS listener per **enabled browser host** (`global.hosts.*`
gated on the owning component's `enabled` — `aurelius-atlas.edge.listeners`
in `_helpers.tpl` builds the list once and `gateway.yaml`/`httproutes.yaml`
both loop the same `fromJsonArray`), and one HTTPRoute per listener with a
single coarse `backendRef` (DD-242 — no per-path split; the webapp's nginx is
the path router). TLS backends (`atlas-server`, `atlas-keycloak`) also get a
`BackendTLSPolicy` (v1) pinning `validation.caCertificateRefs` to the trust CA
Secret and `validation.hostname` to the Service name — the Gateway verifies
the leaf the same way an in-cluster client does. The browser leaf
`atlas-edge-tls` covers
the atlas/dashboard/grafana hosts; the keycloak listener reuses
`<release>-keycloak-tls` (the keycloak chart owns that Certificate — never
re-issue another name for the same hostname, SAN duplication is not free).
`atlas-collector-legacy` (CHT-31) is the webapp's browser-side OTLP token,
generated like every other credential (DD-254) and gated on either consumer.
`<release>-grafana-oauth` (CHT-83, 10.8) is the same two-consumer shape: the
realm import's `${GRAFANA_CLIENT_SECRET}` placeholder (keycloak chart, non-
master only) and the observability chart's `GF_AUTH_GENERIC_OAUTH_CLIENT_
SECRET`; disabling observability alone keeps it (the import still needs it),
master plus no-observability drops it.
The chart **never renders a GatewayClass** — it is a runbook prerequisite
(the cluster's Gateway API implementation is the deployment's choice).
`global.gateway.enabled=false` must take the edge cert with it (a leaf with
no listener is a dangling SAN). With the gateway on and no host resolving to
an enabled component, the render `fail`s — silence here is a misinstall.
The two-hop client-IP trust (DD-261/CHT-32): stock renders trust nothing
(loopback / empty); the `environments/*.yaml` name their pod CIDRs in
`atlas-webapp.nginx.trustedProxyCIDRs` and `atlas-server.forwardedAllowIps`.
That value composes into `AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK` **on one line**
— it is `sed`-substituted into nginx at pod start, and a newline breaks the
substitution.

Helpers are chart-local by design (DD-247): each chart's `templates/_helpers.tpl`
carries the helpers its templates use, following the same naming convention
(`<chart>.fullname`, `<chart>.labels`, …). The convention is the dedupe, not a
shared library — a library chart is a component with no runtime, which is the
abstraction this tree rejects.

## Network segmentation (CHT-60..73)

Two owners, never overlapping (DD-271): the umbrella renders the namespace
default-deny (`<release>-deny-all-ingress`, `podSelector: {}`) plus one
browser-edge allow per enabled listener (`<release>-edge-<host>`, the same
`edge.listeners` gate as the HTTPRoutes — no allow exists for an unrouted
backend); every chart renders only **additive** ingress allows for its own
pods, gated by its own `networkPolicy.enabled`. A chart's switch never
opens the namespace — the deny is the umbrella's alone.

Peers join by **pod** labels — `app.kubernetes.io/name` is the chart-name
constant (`atlas-server`, never release-prefixed) and
`app.kubernetes.io/instance` the release; the observability workloads share
one name and split on `app.kubernetes.io/component`; the pullers and the
bundled Postgres carry fullname-derived name labels (release-prefixed under
a non-matching release). The Service-name joins (`atlas.service` et al.)
rename Services, not pods — never feed them a selector; renaming a peer for
a policy is `networkPolicy.peers.<peer>`. Policies are `<fullname>-ingress`
(one per chart workload-set), Ingress-only (no egress posture in the
charts), and the peer sets are the **verified call graph**: read them off
`helm template` renders, not from docs. Probe ports (collector 13133,
Keycloak management 9000) get no rule — kubelet and port-forward ride the
CNI's node path (CHT-71). `networkPolicy.gatewayNamespaces` (default `[]` =
all namespaces) pins the edge allows' source (DD-272). The contract suite
(`tests/test__charts_*.py`) names every rule id with exact peer sets and
ports — widen a rule and a named rule breaks.

## Gotchas (all hit, all verified on helm 4.3.1)

- `.helmignore` must NOT list `charts/` or `*.tgz` — Helm loads dependency
  archives through the same ignore rules, and the umbrella renders empty.
  `helm/.helmignore-shared` is the curated copy; keep the copies in sync.
- Block sequences: `- name: x` followed by siblings indented to the dash
  (2 columns) is malformed YAML — put the first key 2 columns right of the
  dash (`-   name:`), all siblings aligned.
- Go templates have no `nil` literal — "nil is not a command". Use `""` for
  absent.
- `range` over a missing key throws (nil pointer) — guard with `with`. Deep
  access (`index .Values "x"`).enabled`panics the same way when the map is
absent; read optional component blocks as`index .Values "x" | default dict`.
- On helm 4.3.1, `fromJson` **mis-decodes arrays of objects**: each element
  comes back as a string, so `{{ $l.name }}` fails with "can't evaluate field
  name in type interface {}". Use `fromJsonArray` for lists (elements are
  proper maps) and `index $l "key"` for field access. Single-object
  `fromJson` is fine.
- A chart's `required:` guard fires on BARE renders by design (CHT-02: the
  deployment supplies). Tests/CI pass the chart's `tests/values.test.yaml`.
- `Chart.lock` is committed; resolved dependency tarballs (`**/helm/charts/`)
  are gitignored — `helm dep update` regenerates them. The template/publish
  targets run it first, so a hand-edited component chart is picked up; a bare
  `helm template` against the umbrella is not.

## Adding a chart

1. Create `helm/` inside the owning project (`apps/<app>/helm/`); copy the
   nearest sibling chart's shape.
2. `Chart.yaml`: `name:` is the chart's name (Helm's, for the artifact and
   OCI repository); quote the `description` (an em-dash + colon breaks YAML);
   `version: 0.1.0`, `appVersion: "latest"` (the release rewrites both). No
   `project.json` — the plugin merges `helm-lint`/`helm-template`/
   `helm-publish` onto the owning project from the `Chart.yaml` glob (DD-250).
   The owner needs no release config when it has a `pyproject.toml` (python.ts
   wires the composite module); chart-only owners (no pyproject) set
   `release.version.versionActions: tools/plugins/chart-yaml-version-actions.ts`
   in their `project.json`.
3. Register the component in the umbrella: `Chart.yaml` dependency
   (`version: "=0.1.0"`, `repository: "file://../<owner project>/helm"`,
   CHT-07 pin-equal) and values toggle — the dependency row doubles as the
   umbrella's implicitDependency on the OWNING project (DD-250: the release
   plan and the publish cascade speak in owner names).
4. Copy `helm/.helmignore-shared` to `<chart>/.helmignore`; add
   `tests/values.test.yaml`; run `npx nx run-many -t helm-lint helm-template`
   (CHT-06).

## Removing a slice

A removable component's slice: its `helm/` directory, the umbrella's
dependency row, values toggle, host block, and secret block, and the
deployment reference's topology-table row. The umbrella's dependency row
doubles as its implicitDependency (DD-248), so removing it unwires the
cascade too. Removing a chart leaves its `Chart.lock` entry stale in the
umbrella — run `helm dep update helm` after.

## Commands

```bash
npx nx run-many -t helm-lint helm-template   # the CHT-06 gate
npx nx run <owner-project>:helm-template     # one chart (on its owner, DD-250)
helm template atlas helm -f helm/environments/minikube.yaml -n atlas
helm dep update helm                         # refresh snapshots (gitignored)
```

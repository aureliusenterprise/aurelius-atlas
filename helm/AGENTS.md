# helm/

The umbrella chart of the system (ADR 057), at the **workspace root**: the
umbrella deploys the whole system, so it sits next to the whole repo
(DD-249). Component charts live **next to the project they deploy** —
`apps/<app>/helm/`, `dev/<name>/helm/` (DD-247). Every chart in the tree is
a `helm/` directory; `charts/` is gone. Workspace-wide rules, including the
conversion workflow, live in the root `AGENTS.md`. Increment 10.1 is the
foundation (charts, plugin, CI); the workloads land in 10.2 (stateful),
10.3 (apps + edge), 10.4 (secrets + publish), 10.5 (cluster validation).

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
`storageClass`, `domain`, `issuer.url`, `dnsResolver`.

Names: a release prefixes its charts (`<release>-<chart>`); the fullname
helper drops the prefix when the release name already starts with it, so the
release `atlas` keeps names bare (`atlas-server`) and service DNS matches
what the components' settings reference.

Helpers are chart-local by design (DD-247): each chart's `templates/_helpers.tpl`
carries the helpers its templates use, following the same naming convention
(`<chart>.fullname`, `<chart>.labels`, …). The convention is the dedupe, not a
shared library — a library chart is a component with no runtime, which is the
abstraction this tree rejects.

## Gotchas (all hit, all verified on helm 4.3.1)

- `.helmignore` must NOT list `charts/` or `*.tgz` — Helm loads dependency
  archives through the same ignore rules, and the umbrella renders empty.
  `helm/.helmignore-shared` is the curated copy; keep the copies in sync.
- Block sequences: `- name: x` followed by siblings indented to the dash
  (2 columns) is malformed YAML — put the first key 2 columns right of the
  dash (`-   name:`), all siblings aligned.
- Go templates have no `nil` literal — "nil is not a command". Use `""` for
  absent.
- `range` over a missing key throws (nil pointer) — guard with `with`.
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

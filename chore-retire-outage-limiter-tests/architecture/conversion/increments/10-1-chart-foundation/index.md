# 10.1 Deployment chart foundation

- **Status:** in progress
- **Pull request:** [\#157](<https://github.com/aureliusenterprise/aurelius-atlas/pull/157>)
- **Records:** [ADR 057](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>), DD-240..252

## Scope

The deployment shape of the system, specified once and scaffolded completely: one chart per deployable component, landing in the component's own project (`apps/<app>/helm/`, `dev/<name>/helm/`, DD-247), composed by an umbrella chart, an Nx plugin that lints/renders/publishes charts the way `tools/plugins/docker.ts` does images, and the CI wiring that proves every chart renders on every change.

This increment delivers:

- `helm/` — the umbrella `aurelius-atlas`: composes the component charts, owns the edge (Gateway API), the trust model (cert-manager issuers), and the generated secrets. The one chart without an owning project, so it sits at the workspace root (DD-249).
- `apps/aurelius-atlas-{server,webapp,data2model,lineage-model,validate-entity}/helm` and `dev/{elasticsearch,keycloak,observability}/helm` — the component charts: each owns its component's runtime contract (ports, probes, settings, identity) and its own helpers (DD-247 — no library charts; the naming convention is the dedupe). A chart is not a project (DD-250): the plugin infers its targets onto the owning project — the chart dir's parent — keyed at the owner's root, and wires release there. No `project.json` ships for a chart.
- `tools/plugins/helm.ts` — inferred `helm-lint`, `helm-template`, `helm-publish` targets from each `Chart.yaml`, mirroring the docker plugin's options and CI configurations.
- CI: `helm-lint` + `helm-template` in the validate gate; `helm-publish` in the release workflow.
- `docs/architecture/deployment/index.md` — the deployment reference (topology, environments) and the runbook skeleton the later increments fill.

This increment does not deliver the installable manifests themselves (workloads, services, certificates): they are increment 10.2 (stateful platform), 10.3 (apps and edge), 10.4 (secrets and publish), 10.5 (minikube validation and smoke). The umbrella renders with the component charts present and their workloads gated off, so 10.1's gate is render-level, and 10.5 is where a cluster proves the whole.

## Semantics

| Id | Rule |
| --- | --- |
| CHT-01 | One chart per deployable component plus one umbrella chart; every chart in a release carries the release's version (ADR 019, ADR 057). |
| CHT-02 | A component chart owns its component's runtime contract: container port, probes, settings env (the project's `AURELIUS_ATLAS_*` prefix), trust mounts. The umbrella contains no component knowledge. |
| CHT-03 | The umbrella owns what no component can: the edge (Gateway + routes), the trust issuers, the generated secrets, and the `global.*` values contract every chart reads. |
| CHT-04 | No chart names a cloud provider. Environment difference is values only: domain, issuer, storage class, gateway class, registry. Rendering on a stock cluster is the gate. |
| CHT-05 | Charts publish as OCI artifacts to the registry namespace the images use, under the release tag, by the release workflow (ADR 029's path; signing of chart artifacts is a follow-up). |
| CHT-06 | Every chart lints and renders in CI without a cluster: `helm lint` and `helm template` against the chart's own test values. |
| CHT-07 | The umbrella resolves its component charts at the version equal to its own; a release publishes them together so the tested combination is the shippable combination. |

## Java origin

None. Deployment is Aurelius infrastructure; Apache Atlas ships docker-compose and Kubernetes examples for a Kafka/JanusGraph/Cassandra topology that does not exist here.

## Deviations

None. This increment adds no runtime behaviour.

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green locally and in CI (CHT-06); the CI job renders the umbrella with the minikube environment values (CHT-04).
- A trial `helm install` of the umbrella on minikube (the `minikube.yaml` overlay, locally built images) reaches `deployed` and the three aux Deployments go Ready on their HTTPS `/liveness` probes; `helm upgrade` is a clean no-op. Two aux-chart gaps found by the trial — the unbacked `ca.crt` mount and lineage-model's missing upstream URLs — are deferred to 10.3 (DD-251); the `--wait` stuck-release recovery joins the runbook (DD-252).
- The plugin targets are visible on the owning projects (`npx nx show project aurelius-atlas-server` shows `helm-lint`/`helm-template`/`helm-publish`, DD-250) and `-c ci` selects the CI configuration (CHT-05 wiring).
- Chart tree and umbrella dependencies match the component list of the release (CHT-01, CHT-07) — checked by review of `helm/Chart.yaml` against this spec's Scope.
- The release workflow publishes charts after images (CHT-05) — reviewed as workflow code.

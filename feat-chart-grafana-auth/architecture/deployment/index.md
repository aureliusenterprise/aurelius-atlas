# Deployment

Aurelius Atlas ships as [Helm charts](<https://aureliusenterprise.github.io/feat-chart-grafana-auth/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>): one chart per deployable component, composed by an umbrella chart that a deployment installs. This page is the reference for that shape — what runs, how it is wired, and what a deployment owns. The step-by-step install lives in the [runbook](<https://aureliusenterprise.github.io/feat-chart-grafana-auth/architecture/deployment/runbook/index.md>).

## Topology

Everything runs in one namespace (default: `atlas`), behind one Gateway API edge, on one OIDC issuer:

```
flowchart LR
    browser([Browser]) -->|HTTPS| gw[Gateway<br/>edge]
    gw -->|"/api, TLS"| server[atlas-server]
    gw -->|"atlas.host /, TLS"| webapp[atlas-webapp<br/>nginx]
    gw -->|"keycloak.host, TLS"| keycloak[atlas-keycloak]
    gw -.->|grafana.host, optional| grafana[Grafana]

    server --> es[(atlas-elasticsearch)]
    server --> keycloak
    webapp -.->|browser tokens| keycloak
    subgraph aux [Auxiliary APIs]
        d2m[atlas-data2model]
        lm[atlas-lineage-model]
        ve[atlas-validate-entity]
    end
    aux --> es
    aux --> keycloak
    server --> coll[atlas-observability<br/>collector]
    aux --> coll
    webapp -.->|OTLP web| coll
    coll --> prom[(Prometheus)]
    coll --> loki[(Loki)]
    coll --> tempo[(Tempo)]
    prom & loki & tempo --> grafana
```

The components and their charts:

| Chart | Component | Port | Notes |
| --- | --- | --- | --- |
| `atlas-server` | The Atlas REST API (FastAPI) | 21000/TLS | TLS mandatory in-cluster (SRV-06) |
| `atlas-webapp` | The Atlas dashboard (nginx serving the Angular build) | 8080/TLS | TLS to the last hop (DD-270); `/config.json` resolved at bootstrap (SHL-02) |
| `atlas-data2model` | Natural-language → model API | 21001 | audience/client per chart values |
| `atlas-lineage-model` | Lineage graph API | 21002 | as above |
| `atlas-validate-entity` | Entity validation API | 21003 | as above |
| `atlas-elasticsearch` | Elasticsearch 9 — the system's one store | 9200/TLS | single-node now, HA later |
| `atlas-keycloak` | Keycloak — the one issuer (ADR 007), bundled Postgres | 8443 | issuer URL is immutable once entities exist |
| `atlas-observability` | OTel collector + Prometheus, Loki, Tempo, Grafana | 4317–4321 | the three ingest legs (DD-193/196/202) |
| `aurelius-atlas` | Umbrella: edge, trust, secrets, the `global.*` contract | 443 | composes the eight charts above |

Each component chart lives next to the project it deploys (`apps/<app>/helm/`, `dev/<name>/helm/`, DD-247); the umbrella `aurelius-atlas` is the one chart without an owning project and sits at the workspace root, `helm/` (DD-249). Helpers are chart-local — the naming convention is the dedupe, no library charts.

## The values contract

The umbrella owns what no component can (CHT-03): the edge, the trust issuers, the generated secrets, and the `global.*` block every chart reads — namespace, domain, image registry/namespace/tag/pull secrets, storage class, issuer URL, and the per-component enable toggles. A component chart declares the same `global.*` shape in its own `values.yaml` (with empty defaults) so it renders standalone; through the umbrella, Helm's `global` merge passes the umbrella's values down, and the umbrella is the source of truth.

Chart names in a cluster are `<release>-<chart>`; the release `atlas` keeps them bare (`atlas-server`, `keycloak`…) so service DNS matches what the components' settings reference.

## Environments are values, not forks

CHT-04: **no chart names a cloud provider.** An environment is a values overlay, and the two shipped overlays are the tested shapes:

- `helm/environments/minikube.yaml` — devcontainer/minikube: `envoy-gateway` GatewayClass, self-signed issuer, `*.atlas.test` hosts through `minikube tunnel`.
- `helm/environments/gke.yaml` — GKE (the documented target): the GKE Gateway class, `standard-rwo` storage, the org's ACME/CA issuer.

CI renders every chart against both overlays on every change (CHT-06), so "renders on a stock cluster" is a gate, not a hope.

## Trust

cert-manager signs every certificate (DD-243, corrected by DD-259). The default posture is the chart-created private root: a self-signed bootstrap `Issuer` signs one CA `Certificate` (its Secret is `global.trust.caSecretName`), and a CA-type `Issuer` of that CA — namespaced, since a `ClusterIssuer` cannot read a CA Secret the chart writes into the app namespace — signs every leaf, so every certificate descends from one root and each component's mounted `ca.crt` verifies every peer. A production deployment brings its own issuer (`global.trust.createIssuer: false`, `issuerRef` to the org's, typically a `ClusterIssuer`) and either the CA secret name or a literal CA bundle.

**The Keycloak issuer URL is immutable once entities exist.** Tokens embed the issuer; changing `global.domain` (or `global.issuer.url`) after data is written invalidates every token and every saved reference. Pick the hostname at first install.

## Secrets

Plain Kubernetes Secrets, generated at deploy time (DD-244). The umbrella `randAlphaNum`-generates each credential once and *preserves* it on upgrade via `lookup` — an upgrade never rotates a live password. Values may pin a secret explicitly (a deployment that manages secrets with External Secrets / Vault passes the names in and sets the generator off). The webapp's legacy dashboard token is browser-reachable by design (DD-239) — treat it as a public client's secret.

## Prerequisites a deployment installs

The charts install the system, not the cluster. Before the first install (runbook, step by step):

1. **cert-manager** (CRDs + controller) — the trust model depends on it.
2. **A GatewayClass** for `global.gateway.className` — Envoy Gateway on minikube, GKE Gateway on GKE, any conformant implementation elsewhere.
3. **Pull secrets** (when the registries are private): `dhi.io` for the hardened base images' registry mirrors, `ghcr.io` for the system's own images/charts — passed as `global.image.pullSecrets`.

## Versioning

Chart version == the release semver; `appVersion` == the image tag (`v1.2.3`), so a chart installed by version resolves its component's image by default (DD-245). The umbrella pins its component charts `=x.y.z` to its own version, and `helm package -u` embeds the component tarballs — the published umbrella *is* the tested combination. Charts publish as OCI artifacts beside the images: `oci://ghcr.io/aureliusenterprise/charts/<chart>`.

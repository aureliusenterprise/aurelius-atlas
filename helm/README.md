# helm/

The umbrella Helm chart of Aurelius Atlas (ADR 057). Each deployable component
owns a chart — the container image, ports, probes, settings, and identity of
that component — and the chart lives **next to the project it deploys**
(`apps/<app>/helm/`, `dev/<name>/helm/`, DD-247). This directory holds the
`aurelius-atlas` umbrella — the one chart without an owning project — which
composes them into one installable system: the edge (Gateway API), the trust
model (cert-manager issuers), the generated Secrets, and the `global.*`
values contract every chart reads.

The system's shape — topology, environments, trust, secrets, versioning — is
documented in the
[deployment reference](../docs/architecture/deployment/index.md);
the install sequence in the
[runbook](../docs/architecture/deployment/runbook.md).

## Contents

| Chart                   | Lives in                                   | What it ships                                         |
| ----------------------- | ------------------------------------------ | ----------------------------------------------------- |
| `aurelius-atlas`        | `helm/` (here)                             | Umbrella: edge, trust, secrets, global contract       |
| `atlas-server`          | `apps/aurelius-atlas-server/helm`          | The Atlas REST API (FastAPI on Elasticsearch)         |
| `atlas-webapp`          | `apps/aurelius-atlas-webapp/helm`          | The Atlas dashboard (nginx + Angular, `/config.json`) |
| `atlas-data2model`      | `apps/aurelius-atlas-data2model/helm`      | Natural-language → model API                          |
| `atlas-lineage-model`   | `apps/aurelius-atlas-lineage-model/helm`   | Lineage graph API                                     |
| `atlas-validate-entity` | `apps/aurelius-atlas-validate-entity/helm` | Entity validation API                                 |
| `atlas-elasticsearch`   | `dev/elasticsearch/helm`                   | Elasticsearch 9 (the system's one store)              |
| `atlas-keycloak`        | `dev/keycloak/helm`                        | Keycloak (the one issuer) + bundled Postgres          |
| `atlas-observability`   | `dev/observability/helm`                   | OTel collector, Prometheus, Loki, Tempo, Grafana      |

Quick start (prerequisites and the full sequence in the runbook; commands run
from the repository root):

```bash
helm dep update helm
helm install atlas ./helm \
    -f helm/environments/minikube.yaml --namespace atlas
```

Contributors: read [`AGENTS.md`](AGENTS.md) first — the values contract, the
gotchas, and how to add or remove a chart.

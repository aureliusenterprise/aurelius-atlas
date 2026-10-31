# 10.2 Stateful platform charts

- **Status:** in review
- **Pull request:** [\#158](<https://github.com/aureliusenterprise/aurelius-atlas/pull/158>)
- **Records:** ADR 057, DD-243, DD-244, DD-247, DD-253..260

## Scope

The three stateful platform components become installable workloads: the Elasticsearch store (`atlas-elasticsearch`), Keycloak with its bundled Postgres (`atlas-keycloak`), and the two umbrella pieces every one of them reads — the trust issuer and the generated credentials. This is the first increment whose rendered manifests start real containers on a cluster.

This increment delivers:

- `dev/elasticsearch/helm` — the StatefulSet (root entrypoint → gosu, fsGroup chown replaced by the init-free compose shape), the templated `elasticsearch.yml` ConfigMap, headless + ClusterIP services, the cert-manager `Certificate`, PodDisruptionBudget, the exec `openssl s_client` healthcheck, and the coredump-agent init container fed by the new `aurelius-atlas-elasticsearch-agent` image (DD-255).
- `dev/keycloak/helm` — the `kc.sh start --import-realm` StatefulSet (prod mode, not `start-dev`), the RSS headless service, the realm `ConfigMap` (the committed realm file copied verbatim as a chart asset, its secret placeholders resolved at import by Keycloak's own `replace-placeholders` mechanism fed from the generated Secrets — DD-256), the `Certificate`, PDB, and probes on the management port.
- The bundled Keycloak Postgres (a chart section of `atlas-keycloak`, not a subchart): StatefulSet + Service, the cert-copy init (mktemp + `install -m 600`, tmpfs `/tmp` pinned), the `pg_hba` ConfigMap, VCT, probes.
- `helm/templates/issuer.yaml` — the chart-managed trust root: self-signed bootstrap `Issuer` → `isCA` root `Certificate` → `ca`-type `Issuer`, all namespaced (DD-243 as corrected by DD-259 — one CA for every leaf, so cross-component verification works).
- `helm/templates/secrets.yaml` — the deploy-time credential generation with upgrade preservation (DD-244) for the five secrets 10.2's workloads consume: `<release>-elasticsearch`, `-keycloak-admin`, `-keycloak-database`, `-keycloak-users`, `-otel-clients` (DD-254 re-slices this part of DD-244's promise out of 10.4). The remaining secrets (collector legacy token, and the rest 10.3/10.4 consumers need) land with their consumers.
- A chart-contract pytest suite at the repo root (`tests/`, root project) that renders the charts with `helm template` and asserts the deployment invariants the dev compose already proves (DD-253): the settings keys, the secret shapes, the cert SANs, the realm placeholders.
- The `aurelius-atlas-elasticsearch-agent` image project (`tools/es-coredump-agent/`) so the agent ships through the same build/sign/publish chain as every image.

This increment does not deliver: the app workloads (server, webapp, aux APIs, observability — 10.3), the edge (Gateway/HTTPRoutes — 10.3), the remaining secrets blocks and chart OCI publish polish (10.4), or the scripted minikube install and smoke suite (10.5). The umbrella still installs without a GatewayClass present (10.1's rule stands: the edge resources are gated on values, and 10.2 renders none).

## Semantics

| Id | Rule |
| --- | --- |
| CHT-10 | The store runs as a StatefulSet with a headless Service and a ClusterIP Service; `replicas` defaults to 1 and renders `discovery.type: single-node` with transport TLS off — the DD-006 dev arrangement. `replicas > 1` fails the render in this increment (the quorum-cluster switch is a later increment, named). |
| CHT-11 | `elasticsearch.yml` renders from the chart's values into a ConfigMap mounted over the image's file — the hardened image ignores dotted env vars, so the file is the only settings channel (the dev `config/elasticsearch.yml` is the shape; the contract is: security on, TLS-only HTTP, transport TLS off, ML off, `allow_mmap` false). |
| CHT-12 | The store's HTTP certificate is a cert-manager `Certificate` (the umbrella's issuer, DD-243) with SANs covering `<service>.<ns>`, `<service>.<ns>.svc`, `<service>.<ns>.svc.cluster.local`; it mounts at `config/tls` (never `config/certs` — auto-configuration's directory), as PEM (`<node>.pem`/`<node>-key.pem`) plus the issuer CA as `ca.pem`. |
| CHT-13 | The bootstrap password arrives as `ELASTIC_PASSWORD` from the generated Secret `<release>-elasticsearch` (key `elastic-password`); the chart never renders a password value inline. |
| CHT-14 | Liveness/readiness are exec probes running the compose healthcheck's shape: `openssl s_client` to `localhost:<port>`, CA-pinned, basic-auth, green-or-yellow `/_cluster/health` answers healthy (DD-008). |
| CHT-15 | The coredump agent mounts as an init container from the agent image onto an emptyDir, and `ES_JAVA_OPTS` carries `-javaagent:/agent/coredump-noop.jar` plus the heap flags from values (`-Xms`/`-Xmx` = `heap`); `node.store.allow_mmap: false` stays (GKE `vm.max_map_count`). The pod runs the hardened image's own uid (1000) — it does no root/gosu privilege drop and its JVM refuses root (DD-257) — with `fsGroup: 1000` for the data volume: the in-cluster shape of the compose's separate `volume-init` chown. |
| CHT-16 | Keycloak starts in prod mode (`kc.sh start --import-realm`, never `start-dev`) as the hardened image's uid (65532, which owns the Quarkus build dir — DD-257), `KC_HOSTNAME` = the keycloak host (from `global.domain`/host value — the issuer-pinning warning in the values file and runbook stands), an RSS headless Service for JGroups, HTTPS probes on the management port's `/health/ready` (prod mode puts TLS there too — DD-260), and a `Certificate` for the browser hostname. With the bundled database, the pod waits for it before starting — a `wait-for-postgres` init container, the Kubernetes port of the compose's `depends_on: condition: service_healthy` (DD-258). The realm `ConfigMap` mounts at the import directory. The JVM trusts the cluster CA through the mounted issuer `ca.crt` — `-Djavax.net.ssl.trustStore` is the dev mkcert workaround and is never rendered (the DD-243 trust model); native OTLP export renders only when a collector endpoint is configured (values default: unset — the observability wiring is 10.3). |
| CHT-17 | The bundled Postgres is a chart section of `atlas-keycloak` (it exists only for Keycloak): `dhi.io/postgres:18`, the cert-copy boot (`mktemp -d`, `install -m 600`, `-c ssl=on -c ssl_cert_file=… -c ssl_key_file=… -c hba_file=…`), a `pg_hba` ConfigMap of `local all all trust` + `hostssl all all all scram-sha-256`, a `/tmp` tmpfs pinned `mode=1777`, VCT data, and `pg_isready` probes with `sslmode=verify-full` — whose certificate carries the loopback SAN the probes' dial target needs (`127.0.0.1`, as in the dev `tls.json`; DD-258). `database.flavor: external` swaps the JDBC URL in and renders no StatefulSet. |
| CHT-18 | Every stateful component gets a PodDisruptionBudget `minAvailable: 1` at `replicas: 1`, and `global.storageClass` (or the cluster default when "") backs every volumeClaimTemplate. |
| CHT-19 | The umbrella's `secrets.yaml` generates every empty credential with `randAlphaNum 32` and preserves it across upgrades via `lookup` (DD-244's pattern); 10.2's scope is the five secrets its workloads consume (DD-254). The `Certificate`s and the self-signed issuer chain are the trust model of DD-243 as corrected by DD-259 — the chart-managed root is a namespaced `Issuer` whose one CA signs every leaf; cert-manager is a prerequisite, never installed by the chart. |

## Java origin

None. These are deployment manifests for infrastructure (ADR 047's store, ADR 007's identity provider); Apache Atlas ships compose/k8s examples for a topology this is not (10.1's statement stands).

## Deviations

No Apache Atlas behaviour is ported here, so nothing enters [Deviations](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/conversion/deviations/index.md>). Differences from the dev compose siblings (which are the working reference for these workloads) are recorded where they are decided: no `metrics-puller` sidecars in-cluster (the observability slice's pullers are a 10.3 decision — cluster-native scraping is the shape there), no `mem_limit` (the resource block replaces it), prod-mode Keycloak with no `keycloak.localhost` network alias (the issuer is the environment's host, DD-243), and the issuer CA mount instead of the dev truststore workaround (the DD-243 trust model, CHT-16).

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (CHT-06) — the three dev charts now render workloads, and the umbrella renders issuer + secrets + workloads under both environment overlays.
- The chart-contract suite `uv run pytest tests` (root) names every rule id above via `@pytest.mark.covers("helm", rules=["CHT-14"])`-style markers — renders are asserted against the invariants the dev compose files state (settings keys, secret refs, SANs, probes, hba lines, realm placeholder resolution).
- A hand check (reported in the PR, scripted in 10.5): the umbrella installed on minikube with cert-manager reaches pod-Ready for the store, Postgres, and Keycloak with the generated secrets, no GatewayClass present.
- CI: the agent image builds in `affected -t docker-build`; publish.yaml picks it up with the rest of the image set unchanged.

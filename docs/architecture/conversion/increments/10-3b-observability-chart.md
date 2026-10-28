# 10.3b Observability chart

- **Status:** in progress
- **Pull request:** –
- **Records:** ADR 016, ADR 034, DD-193..196, DD-202, DD-226, DD-239, DD-244,
  DD-254, DD-256, DD-257, DD-265..268

## Scope

The `atlas-observability` chart becomes real: the OTel collector (three ingest
legs, ADR 034's one seam), Prometheus, Loki, Tempo, and Grafana render as
workloads, and the telemetry wiring every earlier increment left dormant turns
on — the apps' per-service leg joins (10.3a rendered them gated), Keycloak's
native OTLP on the legacy leg (10.2 CHT-16's unset endpoint), and the store
slices' metric pullers (the scrape question 10.2 deferred; DD-265 answers it).
The browser leg needs no new wiring: the webapp chart's `/otel/` proxy already
points at the collector Service FQDN (DD-264).

This increment delivers:

- `dev/observability/helm/` — the collector (Deployment + five-leg Service +
  `Certificate` + ConfigMap + issuer-wait init container), Prometheus, Loki,
  Tempo, Grafana (Deployment + PVC + provisioned datasources/dashboards), the
  backend Services, and the `files/` byte-copies of the environment-free dev
  configs (loki, tempo, dashboards, dashboard provider) with the DD-256 drift
  guard.
- The issuer's public name made resolvable in-cluster (DD-265): the
  Keycloak Service gains its `443` port (the public URL's implicit port) and
  the runbook gains the CoreDNS entry — Keycloak's own configuration is
  unchanged, and every consumer keeps the public issuer URL.
- `apps/aurelius-atlas-server/helm`, the three aux charts — the finally-live
  `telemetry.enabled` joins (OTLP endpoint → the collector's per-service leg,
  token URL → the Keycloak Service, client secret → `<release>-otel-clients`).
- `dev/keycloak/helm` — `telemetry.enabled` turns the CHT-16 env block on
  (legacy leg, `<release>-collector-legacy`); its puller moves from the dev
  compose to an in-cluster `metrics-puller` Deployment (DD-266).
- `dev/elasticsearch/helm` — the matching `metrics-puller` Deployment.
- `helm/` (umbrella) — the `-grafana-admin` Secret (CHT-19 pattern) and the
  enablement defaults that make `helm install` a self-observing system
  (ADR 016).
- `tests/test__charts_observability.py` + additions to the umbrella, server,
  keycloak, elasticsearch, and aux chart-contract files.

This increment does not deliver: Grafana-host routing changes (10.3a CHT-32
already routes `grafana.<domain>` when enabled — the backend Service it joins
is this chart's), the alerting/recording rules (none exist to port), chart
publish polish and scripted installs (10.4/10.5).

## Rules

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-33 | The collector runs as a Deployment (contrib image, `dhi.io/opentelemetry-collector:0-debian13-contrib`, image-declared uid + `fsGroup` per DD-257) behind one ClusterIP Service carrying all five ingest ports — browser 4318 (HTTP), per-service 4317 (gRPC) + 4319 (HTTP), legacy 4320 (gRPC) + 4321 (HTTP, values-overridable names, DD-193/DD-196's credential-typed legs) — plus the `metrics` 9464 and `internal` 8888 scrape ports; liveness/readiness are HTTP probes on the `health_check` extension's port (13133).                                                                                                                                                                                                                                                                                                    |
| CHT-34 | The collector's ConfigMap reproduces `dev/observability/config/otel-collector.yaml`'s pipeline — receivers, processors (`resource`, `transform/identity`, `transform/user_labels`, `batch`), exporters, and pipeline memberships — with the environment slots computed from this chart: the single `oidc` provider's `issuer_url` = the public issuer URL (one realm, one issuer, DD-265), `issuer_ca_path`/`ca_file` = `/certs/ca.crt`, backends `http://<fullname>-loki:3100/otlp`, `http://<fullname>-tempo:4318`, prometheus exporter `0.0.0.0:9464` with `send_native_histogram`, and `deployment.environment.name` from values (default `cluster`, DD-268). A test compares the two structures (receiver ports, processor/exporter/pipeline names) so dev and cluster never drift (the DD-256 guard, structural form).     |
| CHT-35 | Ingest auth renders as in dev: the browser and per-service legs use the `oidc` extension (`issuer` + `jwks_url` + `audience: otel-collector`, DD-193/DD-196); the legacy leg uses `bearertokenauth` whose token arrives from `<release>-collector-legacy` (key `token`, DD-239/DD-244) via env — never rendered into the ConfigMap (R5). Receiver TLS uses the chart's own `Certificate` Secret mounted at `/certs`.                                                                                                                                                                                                                                                                                                                                                                                                             |
| CHT-36 | The collector `Certificate` (CHT-14 name-rule join, umbrella chain issuer) carries only cluster names — the Service's bare/`.svc`/`.svc.cluster.local` forms — never a browser host: the collector is producer-facing only (DD-242's audience split). Grafana, Prometheus, Loki, and Tempo serve plaintext on ClusterIP Services; only the collector speaks TLS (ADR 034's seam terminates at its receivers; the stack behind it is one network namespace of trust, DD-242).                                                                                                                                                                                                                                                                                                                                                     |
| CHT-37 | An `issuer-wait` init container (values `collector.issuerWait`, default busybox) waits for the Keycloak Service's HTTPS port and polls its realm well-known endpoint to HTTP 200 before the collector container starts — the Kubernetes port of the dev compose's unbounded `restart: on-failure` for the JWKS boot race (DD-195/DD-226, and the 10.1 values comment's committed shape).                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| CHT-38 | Prometheus runs as a Deployment + PVC (`global.storageClass`, 20Gi default) with the compose's argv (`--config.file`, `--storage.tsdb.path=/var/prometheus`, `--web.enable-otlp-receiver`) and retention (15d); its scrape ConfigMap keeps the five dev jobs and their native-histogram protocol pins (`scrape_protocols: [PrometheusProto, …]`, `scrape_native_histograms: true` on the collector job), retargeted to this chart's Service names (`<fullname>:9464`, `<fullname>:8888`, `<fullname>-loki:3100`, `<fullname>-tempo:3200`, self). No `ServiceMonitor`/`PodMonitor`: there is no Prometheus Operator in this system (DD-266).                                                                                                                                                                                      |
| CHT-39 | Loki and Tempo run as Deployments + PVCs (20Gi) with `files/` byte-copies of their dev configs as ConfigMaps — the DD-256 pattern, byte-identity drift test included. Tempo's OTLP receiver binds 4318 only on the cluster-internal Service the collector exports to (never an ingest leg, never TLS — the collector is the authenticated seam).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| CHT-40 | Grafana runs as a Deployment + PVC with the compose's anonymous-Viewer env set (`GF_AUTH_ANONYMOUS_ENABLED`, `ORG_ROLE=Viewer`, `VIEWERS_CAN_EDIT`), provisioned datasources (uids `prometheus`/`loki`/`tempo` and the `serviceMap`/`tracesToLogsV2` cross-links pinned by test) pointing at this chart's Services, and the seven dashboards as byte-copy ConfigMap assets. Admin: `adminPasswordSecret` joins `<release>-grafana-admin` (the umbrella generates it, CHT-19 pattern); when unset the login form is disabled exactly as in dev (anonymous-only read posture, R5).                                                                                                                                                                                                                                                 |
| CHT-41 | The issuer is reached by its public name from both horizons (DD-265): the Keycloak chart's Service gains a `443` port beside `8443` (both → the browser listener) so `https://keycloak.<domain>/` dials from inside the cluster, and the runbook's cluster prerequisites gain the CoreDNS entry resolving `keycloak.<domain>` to the Keycloak Service (the cluster port of the dev `extra_hosts`, DD-202). Keycloak itself is unchanged (`KC_HOSTNAME` bare, no hostname-v2 options) — the issuer claim follows the request's Host, so the collector's `oidc` provider, the apps' `AUTH_SERVER_URL`/OTLP token URLs, and the pullers' `token_url` all keep the public URL unchanged and now resolve it locally. A hand-check assertion pins that a mint through the Service and a mint through the Gateway yield the same `iss`. |
| CHT-42 | The dormant joins go live with `telemetry.enabled` (server: rendered in 10.3a; aux charts: same joins added here — endpoint = collector 4319, token URL per CHT-41, `OTEL_CLIENT_SECRET` ← `<release>-otel-clients`); the umbrella sets the enablement and the Keycloak `telemetry` block (endpoint = `<collector>:4320`, token Secret = `<release>-collector-legacy`, 0.1 sampler) in its `values.yaml`, so a stock install is a self-observing system (ADR 016) with nothing to remember to switch on.                                                                                                                                                                                                                                                                                                                         |
| CHT-43 | The Elasticsearch and Keycloak charts render a `metrics-puller` Deployment when their `telemetry.enabled` is set (DD-266): the contrib collector image, a ConfigMap port of the slice's dev `metrics-puller.yaml` (receiver credentials from the chart's own Secret joins, `oauth2client` mint against the CHT-41 token URL with the collector's per-service leg as OTLP target, `ca_file` = the mounted trust root), and the dev `service.name` values unchanged (`dev-elasticsearch`, `keycloak-infra`) — the accepted dashboards' `exported_job` pins are the contract, dev and cluster alike (DD-265). The standalone `dev/postgres` slice gets no in-cluster puller here (it is not an umbrella component).                                                                                                                 |
| CHT-44 | Every workload in the chart and both pullers run as the images' declared non-root user with `fsGroup` (DD-257 pattern; the dhi telemetry images all run 65532), drop all capabilities, `allowPrivilegeEscalation: false`, `seccompProfile: RuntimeDefault`; no credential ever renders into a ConfigMap (R5 — bearer/JWKS material is Secret/env-only); the stack gets no PDB (its loss degrades telemetry, never the data path).                                                                                                                                                                                                                                                                                                                                                                                                |

## Java origin

None — this increments ports no Apache Atlas behaviour. The reference for every
rule is the dev compose stack (`dev/observability/docker-compose.yaml` and
`config/`), the 7.17/7.18 ingest-auth increments, and ADR 016/034.

## Deviations

None against Atlas. Differences from the dev compose siblings, recorded where
decided (design log): DD-265 (split-horizon issuer: a runbook CoreDNS entry
resolves `keycloak.<domain>` to the Service and the Service gains its `443`
port — the cluster port of the compose's `keycloak.localhost`/`extra_hosts`,
with Keycloak and every consumer configured identically in both shapes),
DD-266 (static scrape configs + slice puller Deployments; no Prometheus
Operator, no sidecar pullers), DD-267 (Grafana admin Secret generated by the
umbrella; login stays disabled when unset), DD-268
(`deployment.environment.name` from values, default `cluster`; the compose
keeps `development`).

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green — the observability chart
  renders five workloads + Services + PDB-free config, the umbrella renders
  with `atlas-observability` enabled, and the two store charts gain the puller
  renders.
- `tests/test__charts_observability.py` names CHT-33..44; the config drift
  guards (byte copies + the CHT-34 structural pin) run in the same suite; the
  server/aux/keycloak/elasticsearch/umbrella chart files grow their telemetry
  rules.
- Hand check (reported in the PR, scripted in 10.5): the full umbrella on
  minikube _with_ observability enabled (minus 10.3a's `--set
atlas-observability.enabled=false`); every pod Ready; a scripted legacy-leg
  round-trip — a `curl` OTLP push with the `-collector-legacy` bearer to
  `:4321` through a port-forward (or an in-cluster producer), then the series
  read back from Prometheus (`kubectl exec`/port-forward `:9090/-/ready` +
  query); Grafana responds 200 through `grafana.<domain>` when
  `global.hosts.grafana.enabled` is flipped for the check; collector OIDC leg
  proven by a minted client JWT accepted and an anonymous push answered 401.
- CI: `nx affected -t test e2e -c ci` green (the compose-based suites are
  unchanged — the dev shape stays; the charts ride the render gates).

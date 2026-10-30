# 10.6 Network segmentation

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-271, DD-272 (pre-pentest review findings H2/M10)

## Scope

The system runs as one flat, meshed namespace today: any pod can dial
Elasticsearch, Postgres, Keycloak, the collector legs, and every workload's
port. This increment adds **ingress segmentation** to every chart: a
namespace-wide default-deny rendered by the umbrella, and one scoped
allow-list per workload, joined by the CHT-13 name rule like every other
cross-component join. This is a deployment-plane increment (no Atlas
behaviour, no REST surface).

This increment delivers:

- `helm/templates/networkpolicy-deny-all.yaml` — the namespace-wide
  default-deny-ingress policy (the umbrella owns the namespace contract).
- `templates/networkpolicy.yaml` in each component chart that owns an
  in-cluster allow: `atlas-server` (webapp, lineage-model),
  `atlas-data2model` (lineage-model), `atlas-elasticsearch` (server, its
  puller), `atlas-keycloak` (the minters, jgroups, and its bundled Postgres:
  Keycloak + its puller), `atlas-observability` (collector legs per
  producer, Prometheus/Loki/Tempo scrape/export/panel joins). The webapp and
  Grafana own no chart-side allow — their only ingress is the umbrella's
  gateway rule, so their charts render no policy file.
- `global.networkPolicy.gatewayNamespaces` (the umbrella contract) naming
  the Gateway data-plane namespaces, so the browser-facing listeners can be
  pinned instead of left open.
- `tests/test__charts_*.py` additions pinning every policy's peers and
  ports (the edge allows in `test__charts_edge.py`, the in-cluster allows
  at each chart's own suite).

This increment does not deliver: egress policy (CNI-agnostic ingress only,
CHT-73), per-tenant or multi-namespace shapes (out of scope), the Grafana
SSO policy amendment 10.7 needs (its own diff), or tightened
`set_real_ip_from`/`forwardedAllowIps` CIDRs — with this increment the
reachable set equals the trusted set, which retires most of the M10
exposure; the CIDRs stay a second line of defense.

## Semantics

`NetworkPolicy` peers are **pod selectors derived from the name rule** (the
same `<release>-<chart>` derivation the Services use — a component renamed
via `fullnameOverride` renames its selector too, CHT-70). Ports are
container ports. A chart's policies render unless its `networkPolicy.enabled`
is set false (default true), and setting it false changes nothing else in
the render (CHT-72).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-60 | The umbrella renders exactly one namespace-wide `NetworkPolicy` (`<release>-deny-all-ingress`, `podSelector: {}`, `policyTypes: [Ingress]`, no ingress rules) while `networkPolicy.enabled` (default true). No component chart renders a default-deny; component policies are purely additive allows.                                                                                                                                                                                                                                                                                                                               |
| CHT-61 | The webapp's 8080 accepts ingress from the Gateway data plane only: when `global.networkPolicy.gatewayNamespaces` is non-empty, one `namespaceSelector` per named namespace; when empty, all namespaces (the honest default for a public browser edge whose data-plane placement varies per cluster — the runbook names the pin). No in-cluster workload is added to this rule.                                                                                                                                                                                                                                                     |
| CHT-62 | The Keycloak pods accept 8443 from the pods that hold realm/ingest credentials against it — server, the three aux APIs, both metrics pullers, the collector (JWKS + issuer-wait) — plus the gateway edge rule of CHT-61 (same fallback), and 7800 (jgroups) from Keycloak pods. Nothing else may reach it; the management port gets no allow rule (CHT-71).                                                                                                                                                                                                                                                                         |
| CHT-63 | The bundled Postgres accepts 5432 from the Keycloak pods and the Keycloak metrics puller only. (An `database.flavor=external` render moves the target off-cluster; no policy for it is this chart's to render.)                                                                                                                                                                                                                                                                                                                                                                                                                     |
| CHT-64 | Elasticsearch accepts 9200 from the server pods and its own metrics puller only. 9300 (transport, single-node) has no allow rule — denied by absence.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| CHT-65 | The server accepts 21000 from the webapp pods (the `/api/` proxy) and the lineage-model pods (its `ATLAS_BASE_URL` join) only (the chart's own policy). A gateway allow for the server (container port `global.hosts.dashboard.port`) is rendered **by the umbrella** exactly when `global.gateway.enabled` and `global.hosts.dashboard.enabled` — the same gate as the dashboard HTTPRoute: who the edge exposes is the umbrella's fact, and no allow exists for an unrouted backend.                                                                                                                                              |
| CHT-66 | data2model accepts 21001 from the lineage-model pods (its `DATA2MODEL_URL` join) only. The lineage-model and validate-entity charts render no ingress allows: nothing in this system dials them (their clients are external through the gateway or future increments; a policy that opened them would be a lie about a caller that doesn't exist).                                                                                                                                                                                                                                                                                  |
| CHT-67 | The collector's legs accept, per producer: 4318 (browser leg) from webapp; 4317/4319 (per-service legs) from server, the three aux APIs, and both metrics pullers; 4320/4321 (legacy legs) from webapp and Keycloak; 9464/8888 (scrape) from Prometheus. The health port 13133 gets no rule (CHT-71).                                                                                                                                                                                                                                                                                                                               |
| CHT-68 | Prometheus 9090 accepts Prometheus (self-scrape) and Grafana (panels); Loki 3100 accepts the collector (export), Prometheus (scrape), and Grafana (datasource); Tempo 4318 accepts the collector only (its OTLP ingest), and Tempo 3200 accepts Prometheus (scrape) and Grafana (datasource).                                                                                                                                                                                                                                                                                                                                       |
| CHT-69 | Grafana gets no chart-owned ingress allow (no in-cluster caller dials it; Prometheus does not scrape it): its only allow is the umbrella's gateway→Grafana policy (`global.hosts.grafana.port`), rendered exactly when the Grafana host is enabled — default off, so a stock install's Grafana is reachable only by `kubectl port-forward`, which rides the kubelet and is policy-exempt (the runbook's documented access path).                                                                                                                                                                                                    |
| CHT-70 | Every peer selector joins the peer's **pod labels** — `app.kubernetes.io/name` = the peer's chart name (its puller/postgres the fullname-qualified name), `app.kubernetes.io/instance` = the release, plus `app.kubernetes.io/component` where one chart's pods share a name (the observability workloads). The local join overrides (`atlas.service` et al.) rename Services, not pods, and never feed a selector; renaming a peer for a policy is `networkPolicy.peers.<peer>` (the pod-name label). Policies are `<fullname>-ingress`, one per chart workload-set, gated by that chart's `networkPolicy.enabled` (default true). |
| CHT-71 | No policy opens a probe-only surface: the collector's 13133 and Keycloak's management 9000 appear in no ingress rule. Kubelet probes ride the node and are exempt under the CNIs this project runs (documented assumption, not a policy).                                                                                                                                                                                                                                                                                                                                                                                           |
| CHT-72 | `networkPolicy.enabled=false` (umbrella or any chart) removes exactly that scope's policies; every other resource renders byte-identically.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| CHT-73 | Every policy is `policyTypes: [Ingress]` only — no egress restriction (a deny-by-default-egress posture is a cluster-policy decision, not a chart one; the compose dev shape has no policies at all and stays byte-identical).                                                                                                                                                                                                                                                                                                                                                                                                      |

## Java origin

None — this increment ports no Apache Atlas behaviour. The reference is the
pre-pentest review of the 10.x charts (findings H2, M10) and the CHT-13 name
rule.

## Deviations

None against Atlas. Differences from the dev compose: the compose stacks run
with no network policy at all (a dev convenience); the cluster shape
segments from the first install. Recorded in the design log as DD-271 (the
default-deny/allow-list ownership split) and DD-272 (the gateway-source
knob and its all-namespaces fallback).

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (the nine owners).
- `tests/test__charts_umbrella.py` names CHT-60/72/73;
  `test__charts_edge.py` CHT-61 and the umbrella halves of CHT-62/65/69 (the
  per-listener gateway allows, their gates, and the namespace pin);
  `test__charts_keycloak.py` CHT-62 (in-cluster minters) /63/71;
  `test__charts_elasticsearch.py` CHT-64; `test__charts_server.py` CHT-65;
  `test__charts_aux.py` CHT-66; `test__charts_observability.py`
  CHT-67/68/69/70. Each test pins the exact peer selectors and ports, so a
  renamed join or a widened rule breaks a named rule, not a snapshot.
- Hand check (reported in the PR, scripted in 10.5): the full umbrella on
  minikube — the system still boots and the 10.3b leg round-trip still
  passes with the policies on; a negative check — an unrelated in-cluster
  pod (a `curl` pod) gets no answer from `atlas-elasticsearch:9200` and
  `atlas-keycloak-postgres:5432`, and answers from `atlas-server:21000` only
  once it pretends to be the webapp by being deleted from the allow-list's
  view (port-forward exempt, direct dial denied).
- CI: `nx affected -t test e2e -c ci` green (the compose suites are
  unchanged — policies are cluster-only resources).

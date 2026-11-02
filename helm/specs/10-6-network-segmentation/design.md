# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-271. Network-policy ownership: the umbrella deny-all and the chart's additive allows

- **Status:** Accepted
- **Increment:** 10.6
- **Date:** 2026-10-29

**Context.** The pre-pentest review's H2 found the cluster shape flat: any
pod in the namespace could dial any other pod's every port, so one webapp
compromise walked to Elasticsearch's 9200, Keycloak's 8443, and the telemetry
backends without a credential check at the network layer. Kubernetes
`NetworkPolicy` is the native fix, but its semantics — policies are additive
allows and a namespace is default-open until some policy selects a pod —
make _ownership_ the design question: a single umbrella-owned policy set
would have to enumerate every chart's ports (a central registry the component
charts don't have, against ADR 057's per-chart ownership), and one default
rendered per chart would make a chart's `networkPolicy.enabled=false` a
namespace-wide open — the opposite of the surgical switch operators need.

**Decision.** Two owners, never overlapping (CHT-60/72): the umbrella renders
exactly one namespace-wide deny (`<release>-deny-all-ingress`,
`podSelector: {}`, no rules) and the browser-edge allows for its own
listeners; every chart renders only additive ingress allows for the pods it
owns, gated by its own `networkPolicy.enabled`. Disabling a chart's switch
narrows allows, never the deny — no component can open the namespace, and no
component chart ever needs to know the namespace contract exists. Peers join
by **pod** labels (`app.kubernetes.io/name`/`instance`/`component`, CHT-70),
not Service names: the name rule the Services use is the same rule, and the
`networkPolicy.peers.<peer>` overrides exist because the Service-name joins
(`atlas.service` et al.) rename Services and must never feed a selector. The
peer sets are the full call graph read off the renders (who actually dials
whom, DD-265's split-horizon included), so every rule names a real caller —
lineage-model and validate-entity get no ingress policy because nothing dials
them (CHT-66), and Grafana's only allow is the gateway's when its host is
enabled (CHT-69).

**Alternatives.** (a) One umbrella-owned policy list — rejected: centralises
every chart's port knowledge in the umbrella, exactly what ADR 057 split up,
and a component renamed by values silently breaks a rule it does not own.
(b) Per-chart default-deny policies — rejected: overlapping denies compose to
the intersection and a chart's disable switch becomes namespace-wide
foot-gun. (c) CiliumNetworkPolicy / egress rules — rejected: a CRD
dependency for a posture Kubernetes v1 covers, and egress restriction is a
cluster-policy decision (the compose dev shape runs with no policies at all;
CHT-73 keeps Ingress-only so both shapes stay honest). (d) AdminNetworkPolicy
— rejected: out of the chart's namespace scope entirely.

**Consequences.** The umbrella and every chart carry a
`networkPolicy.yaml`; the contract suite names CHT-60..73 with the exact
peer sets and ports so a widened rule breaks a named rule, not a snapshot.
Kubelet probes and `kubectl port-forward` ride the CNI's node path and are
policy-exempt — documented (CHT-71), which is what keeps the collector's
13133 and Keycloak's 9000 rule-free. A cluster upgrade applies the deny the
moment it rolls: charts that ship a policy whose caller the operator has
customised need the `peers` override set before the upgrade, and the hand
check (10.5 script) boots the full umbrella under the policies before the
leg round-trip runs. Next free DD: 272.

### DD-272. The edge allow's source is a knob with an all-namespaces default

- **Status:** Accepted
- **Increment:** 10.6
- **Date:** 2026-10-29

**Context.** The gateway edge policies (CHT-61) admit the Gateway's data
plane to the browser backends' container ports. The obvious `from` is the
data plane's namespace by label — but the placement is not the chart's fact:
Envoy Gateway ships its data plane wherever its own install puts it
(`controlPlane.namespace`), the managed alternatives (GKE, AKS, Istio
ingress) name it their own, and the dev kind/minikube shapes may co-locate
it. A wrong pin does not fail loudly: the HTTPRoutes stay green, the Gateway
programs, and every browser request black-holes at the network layer —
exactly the class of failure the pentest would report as a foot-gun.

**Decision.** `networkPolicy.gatewayNamespaces` (list, default `[]`). Empty —
the shipped default — renders `namespaceSelector: {}` (every namespace):
the browser backends are already public through the Gateway, so an
all-namespaces source adds no exposure the edge does not already have —
the in-cluster peers of a browser backend are no closer to a secret than a
browser is (the webapp proxies only through the server's own auth). A
non-empty list pins: one `namespaceSelector` per name matched on
`kubernetes.io/metadata.name`, and only those namespaces admit. The runbook
names the pin as the production hardening step; the chart cannot read the
Gateway's placement from inside the release.

**Alternatives.** (a) Default to `ingress-gateway` (Envoy Gateway's default
namespace) — rejected: right for one install recipe, silently wrong for the
managed platforms, and the failure mode (black-holed edge) is invisible in
the HTTPRoute tests. (b) Discover the data plane from the cluster at render
— rejected: `helm template` has no cluster, and an `lookup`-based default
makes the render untestable (the contract suite renders offline, CHT-06).
(c) No knob at all, always all-namespaces — rejected: operators on a
multi-tenant cluster lose the hardening path entirely.

**Consequences.** The stock install's edge policies say "any namespace", which
reads alarming in a security review until DD-272 is cited — the spec and
`helm/values.yaml` comment carry the pointer. The pin test (CHT-61) renders
the single-namespace spellings so the knob is a contract, not a suggestion.
A future environment overlay (helm/environments/) may set the pin per
platform once the placement facts are on record.
Next free DD: 273.

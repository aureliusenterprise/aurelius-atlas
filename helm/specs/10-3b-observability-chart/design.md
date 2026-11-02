# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-265. The issuer's public name resolves inside the cluster too (split-horizon)

- **Status:** Accepted
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** The public issuer host (`keycloak.<domain>`) is made resolvable
_in-cluster_ as well: the runbook's cluster setup gains one CoreDNS entry
(rewrite `keycloak.<domain>` → `atlas-keycloak.<ns>.svc.cluster.local` — the
cluster port of dev's per-producer `extra_hosts`, DD-202), and the Keycloak
chart's Service gains a `443 → https` port so the public URL's implicit port
dials. Keycloak's configuration is unchanged (`KC_HOSTNAME` stays the bare
public host — the hostname-v2 options are not enabled) and no consumer
changes: the collector's `oidc` extension, the apps' `AUTH_SERVER_URL`, the
OTLP token URLs, and the pullers' `token_url` all keep the public URL and now
resolve it locally. The collector keeps one `issuer_url` (no `jwks_url`
split). The hand check pins that a mint through the Gateway and a mint
through the Service yield the same `iss`.

**Reason.** The cluster must answer 10.2's deferred "how do in-cluster
producers reach the issuer" question, and a live probe against the 10.3a
hand-check cluster pinned the constraints. Keycloak (26.7, hostname v1,
`KC_HOSTNAME` bare, `KC_PROXY_HEADERS=xforwarded`) resolves the emitted
issuer from the _Host header_: a request with `Host: keycloak.atlas.test`
mints `iss=https://keycloak.atlas.test/realms/master`; one with the Service
FQDN as Host mints `iss=https://atlas-keycloak.atlas.svc.cluster.local/realms/
master` — a different issuer, permanently embedded in every token it
produces (runbook §0). So in-cluster consumers cannot simply dial the Service
name: they would fork the issuer per dial-path. The discovery document makes
it worse: it hands out a `jwks_uri` that follows the same Host, and the
auth library (and every OIDC client) _follows_ it — a Service-FQDN fetch
returns a jwks_uri that only makes sense on the dial path it came from. The
one shape where every consumer keeps its configuration and every token keeps
the canonical `iss` is making the public name resolvable both outside
(the Gateway route, browsers) and inside (CoreDNS → Service, pods), i.e.
split-horizon DNS — and that is precisely the mechanism the dev stack
already runs: `keycloak.localhost` is in every producer's hosts file
(Docker's `extra_hosts`) so the single issuer name resolves wherever it is
dialled. A real deployment's DNS does the same naturally (`atlas.test` is
the operator's domain, its internal view points at the cluster); on a dev
cluster the CoreDNS entry is the explicit form, and it is a documented
cluster prerequisite beside cert-manager and the GatewayClass.
The Service's second port exists because `https://keycloak.<domain>/`
dials 443 and the public URL must carry no port for the canonical `iss`
(Host-with-port → issuer-with-port).

**Alternatives.** (a) The hostname-v2 split (`KC_HOSTNAME_URL` +
`--hostname-backchannel-dynamic`): Keycloak's own answer to internal-vs-
public URLs — rejected: it makes the _claim_ path-dependent (the
backchannel's issuer follows the dial name per request), and the probe
showed even v1's port handling varies by dial path (:8443 appears in `iss`
whenever the Host header carries it), so the permanent claim would fork
per producer. (b) A per-consumer fetch/claim split (the collector's native
`jwks_url`, a new option in `aurelius-atlas-auth` to fetch JWKS at the
Service while checking the public `iss`, Service-FQDN token URLs in every
chart): rejected — it touches the auth library, three aux apps' settings,
the pullers, and the collector to work around a DNS gap the cluster owns,
and any future discovery-following component (Grafana/Tempo OIDC, the
server's own auth when it lands) inherits the same surgery. (c) A headless
ExternalName Service for the public name: Services answer at
`<name>.<ns>.svc.cluster.local`, never at a bare host — impossible.
(d) `hostAliases` per pod: wants an IP (Service ClusterIP is unknown at
render time). (e) Route in-cluster mints through the Gateway (hairpin via
Envoy with a Host rewrite): rejected — httpx/http clients cannot present
`Host: keycloak.<domain>` over a Service-IP connection without bespoke
transports, and Envoy hairpins every internal token mint.

**Consequences.** The runbook gains the CoreDNS step (the minikube line:
`kubectl -n kube-system edit cm coredns`, a `rewrite name` stanza); the
hand check scripts it and the `helm upgrade` pins it.
`tests/test__charts_keycloak.py` pins the Service's `443 → https` port and
the unchanged `KC_HOSTNAME`. The dashboard/contract rule stays honest: one
realm, one issuer URL, two horizons of DNS for the same name — the same
sentence the dev compose already tells.

### DD-266. Scrape with static configs and slice-owned puller Deployments

- **Status:** Accepted
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** 10.2's deferred scrape question is answered with the compose's
shape, not Kubernetes-native service discovery: the Prometheus ConfigMap
keeps the five dev jobs (`prometheus`, `otel-collector` with the
native-histogram protocol pins, `otel-collector-internal`, `loki`, `tempo`)
retargeted to this chart's Service names, and the Elasticsearch and Keycloak
charts each gain a `metrics-puller` Deployment gated on `telemetry.enabled` —
the contrib collector image, a ConfigMap port of the slice's dev
`metrics-puller.yaml`, the dev `service.name` values kept verbatim
(`dev-elasticsearch`, `keycloak-infra`). No `ServiceMonitor`/`PodMonitor`
resources anywhere; no sidecar pullers.

**Reason.** The accepted Grafana dashboards pin `exported_job` values
(`dev-elasticsearch`, `keycloak-infra`, `keycloak`, …) that came from the
pullers' `service.name` upserts, and 10.2's spec committed to
"cluster-native scraping" only as a prediction, not a contract. A
Prometheus-Operator install contradicts the deployment reference's component
list (the stack is five images, and the Operator is a sixth with its own
CRDs); static scrape configs are what the working reference already runs and
what the stack dashboard's `job="otel-collector"` pins assume. Puller-as-
Deployment (not sidecar) keeps 10.2's store charts' statefulsets untouched
— including the CHT-18 template-hash checksums — and gives each puller its
own restart/rollout blast radius, which is what the dev `restart:
on-failure` + ESD-06 lesson (a wedged puller starves the store's telemetry
silently) asks for as a separate unit. Keeping the dev `service.name` values
is deliberate (DD-265's one-contract rule): a dashboard must not fork per
environment, and `dev-` reads as the metric-family name the dashboards were
accepted with, not as a lie about the environment (that's
`deployment.environment.name`, DD-268).

**Alternatives.** (a) `ServiceMonitor`s via Prometheus Operator — rejected
above (component budget, CRD surface, dashboards' job pins). (b) Puller as
a second container in each store pod — rejected: store rollout churn, and
the store's probes/checksums now include a telemetry concern. (c) Rename
`service.name`s to environment-neutral values and edit the dashboards —
rejected: the dashboards are the accepted surface (this increment's own
byte-copy drift guards treat them as frozen); a values-level
`service.name` override is available for a deployment that wants its own
attribution. (d) Scrape Elasticsearch/Postgres with Prometheus' native
`elasticsearch`/`postgres_exporter` jobs — rejected: needs an exporter
image not in the stack, and the OTel `elasticsearch`/`postgresql` receivers
already produce the series the dashboards query.

**Consequences.** `test__charts_elasticsearch.py`/
`test__charts_keycloak.py` grow a puller render (gated off by default — the
dev compose remains the dev shape); the puller ConfigMaps are structurally
compared against the dev YAMLs (CHT-34's pin, same pattern). The umbrella
enables `telemetry.enabled` on both store charts so a stock install gets
store metrics. `dev/postgres`'s standalone puller stays compose-only — that
slice is not an umbrella component. Next free DD: 267.

### DD-267. Grafana's admin password is a generated Secret and the login form stays disabled

- **Status:** Accepted (the login-form-stays-disabled clause superseded by
  [DD-276](../../../dev/observability/specs/10-8-grafana-auth/design.md#dd-276-grafana-logs-in-through-the-realm-with-a-request-derived-root-url))
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** The umbrella generates `<release>-grafana-admin` (user +
password, the lookup/values/fresh-`randAlphaNum` CHT-19 pattern) and the
observability chart joins it into `GF_SECURITY_ADMIN_USER` /
`GF_SECURITY_ADMIN_PASSWORD` when `grafana.adminPasswordSecret` is unset
(default) or names a Secret to use. The login form stays disabled
(`GF_AUTH_DISABLE_LOGIN_FORM=true`) exactly as in dev, so the deployed
posture is anonymous-Viewer read access and the admin credential is held in
the Secret for the operator to use through whatever authenticated path the
environment opens later. A deployment that brings its own Secret points
`adminPasswordSecret` at it and the umbrella generates nothing.

**Reason.** The values contract already reserved the hook ("the default
posture is kubectl port-forward"), and the CHT-19 pattern — one generated
Secret per credential, preserved across upgrades, never rendered into any
ConfigMap — is what every other credential in this system follows (DD-254).
The alternative in dev (no admin password at all, Grafana's `admin`/`admin`
default) is what R5 forbids shipping, and enabling the login form would put
a password-authenticated surface behind the `grafana.<domain>` route (10.3a
CHT-32) that has no Keycloak front — the edge's OIDC auth filter covers the
atlas host, not this one, and bolting auth onto the observability host is
its own increment-sized decision, not a side effect of turning the stack on.
Keeping the form disabled matches the accepted dev contract: anonymous Viewer
is the posture; the generated admin exists so the instance is never
ship-default-credentialed.

**Alternatives.** (a) `adminPassword` in values plaintext — rejected: R5,
and the chart's whole secrets story is generation + joins. (b) No admin at
all — rejected: Grafana still boots `admin`/`admin` internally and the form
being off is the only thing gating it; the operator needs a real credential
to re-enable it deliberately. (c) Route Grafana through Keycloak now —
rejected as scope: the edge's auth filter pattern exists, but wiring it is
an edge change with its own rules (10.4's polish list has the candidates).

**Consequences.** `helm/templates/secret-grafana.yaml` (or the existing
secret template's sibling block) renders the pair only when
`atlas-observability.enabled` and `grafana.enabled`; the observability test
pins the `valueFrom` joins. Turning `GF_AUTH_DISABLE_LOGIN_FORM` off in a
values overlay is the documented way to expose admin, with the Secret
retrieved per the runbook's `kubectl get secret` line. Next free DD: 268.

### DD-268. The cluster's deployment environment is named by values, not baked as development

- **Status:** Accepted
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** The collector's `resource` processor upserts
`deployment.environment.name` from `collector.deploymentEnvironment`
(default `cluster`); the dev compose's ConfigMap keeps `development`
untouched. Producers contribute no environment attribute of their own (the
OTel SDK defaults stay unset — the charts render no `OTEL_DEPLOYMENT_*`
env); the collector is the single place the attribute is stamped, in every
deployment shape.

**Reason.** The dev config's `development` value is an environment
statement, not pipeline semantics — every rule CHT-34 copies (receivers,
processors, pipelines) is environment-free except this one line, and the
charts' contract is "the dev config's shape with the environment slots
computed" (the observability values file's own comment). Baking
`development` into a cluster install would make Tempo/ Loki's data lie about
where it came from, and an operator filtering panels by environment would
have to fork the ConfigMap — the drift DD-253's suite exists to prevent.
Defaulting to `cluster` keeps a stock install honest with zero values; the
attribute's consumer contract (the OTel semantic convention, and panels that
group by it) is unaffected. A producer-side `OTEL_RESOURCE_ATTRIBUTES`
route was the other shape: rejected because then every chart would stamp
the same environment string (eight places instead of one) and any mismatch
between them silently splits the panels' filters.

**Alternatives.** (a) `deployment.environment.name` from the umbrella's
release/environment values (e.g. `global.environment`) — considered; kept
chart-local as `collector.deploymentEnvironment` because the collector is
the stamper and there is no second consumer of the concept yet; promote it
to `global.*` when a second one appears. (b) Producer-side env — rejected
above. (c) Omit the attribute in-cluster — rejected: Tempo's
`deployment.environment` search facets and the resource processors'
matching depend on a value existing.

**Consequences.** The CHT-34 structural test compares dev vs cluster configs
everywhere except this attribute's value (the one slot the test knows to
allow); a values-level override is the documented fork. Next free DD: 269.

### DD-269. The boot-gate image is curl, not busybox: wget cannot handshake Keycloak's TLS

- **Status:** Accepted
- **Increment:** 10.3b

**Context.** The hand check's first live boot left the three `issuer-wait` init
containers spinning forever with the issuer healthy: busybox's `wget`
(`--no-check-certificate`) fails Keycloak's TLS listener with `got bad TLS
record (len:0) while expecting handshake record` / `Connection reset by peer`
against a server openssl, python, and curl all complete handshakes to
(TLS 1.2 and 1.3, ECDHE-RSA-AES256-GCM-SHA384 and TLS_AES_256_GCM_SHA384).
The uClibc busybox TLS stack is the failing side, and it fails on every
attempt — an init loop with a fixed `sleep` would never end, so a workload
whose whole job is "wait for the issuer" blocks the collector, the server
puller, and the Keycloak puller forever.

**Decision.** The issuer-wait init ships as `dhi.io/curl:8` (uid 65532, as
busybox did) with `curl -sSf --insecure --retry 0 --retry-connrefused
--retry-delay 5 <well-known>` — an infinite native retry, no `sh` needed
(the hardened curl image has no shell), exit 0 the moment the realm answers.

**Alternatives.** (a) A richer init image with a shell (alpine-class) —
rejected: one more base image to harden for a six-line poll, and the retry
semantics are identical. (b) A TCP-only wait (`nc -z`) — rejected: a listening
socket does not mean the realm's JWKS endpoint answers, and the OIDC extension
reads exactly that endpoint (DD-195's race is an HTTP-level one). (c) Keep
busybox, retry the init from Kubernetes instead of in-process — rejected: a
backoff-waiting Pod is exactly what the init container exists to prevent
(DD-298's lesson applies to crash-looping inits too).

**Consequences.** CHT-37's rule text names the image honestly; the chart tests
pin `dhi.io/curl:8` and the command shape (no shell, `--retry-connrefused`).
The `--insecure` flag stays scoped to a boot gate (the collector verifies the
issuer CA-pinned, DD-216). Next free DD: 270.

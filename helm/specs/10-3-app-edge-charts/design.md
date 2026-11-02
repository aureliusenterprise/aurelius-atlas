# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-261. The two-hop edge names both client-IP trust hops

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** In-cluster the browser path is Gateway → webapp nginx →
server, and both proxy hops are named in values: the webapp's nginx gains a
`realip` block (`set_real_ip_from` from `nginx.trustedProxyCIDRs`, the
Gateway's network, an environment value) resolving `X-Forwarded-For` to the
browser before the `limit_req` geo bucket and the access log key on it; the
server's `FORWARDED_ALLOW_IPS` takes the webapp's network. Both default to
no-trust (loopback / empty) in a stock render; the environment overlays name
their clusters' pod CIDRs (`10.244.0.0/16` on minikube). The nginx change
lands in the app's own `nginx.conf.template` (with a placeholder the chart
resolves), keeping the chart's byte-copy and the e2e mirror one contract —
the e2e stack is one hop and sets no trusted proxies, so its behaviour is
unchanged.

**Reason.** DD-238's rate-limiter design rests on one fact: "the browser
cannot spoof the TCP address nginx sees" — true when nginx is the front
door. The Gateway API edge (DD-285) makes the browser's TCP address, as
nginx sees it, the Gateway's. Left unnamed, every browser behind the gateway
shares one `limit_req` bucket (the Gateway's address, inside the RFC1918
geo allowlist → the limiter disables entirely: requests with an empty key
are not accounted), and the server's access log/peer attributes key on the
wrong pod. That is not a hypothetical deployment shape; it is the product's
default edge. DD-238's consequence line ("deployments that front the server
with something other than the webapp nginx get no limiter") anticipated a
foreign front end, not this one in front of the nginx itself.

**Alternatives.** (a) Keep nginx's TCP-trust and let the geo allowlist
swallow the gateway — rejected: it silently disables the only browser rate
limiter in the product (DV-87's alert-drawer UX would fire against one
shared bucket, or never fire). (b) Trust `X-Forwarded-For` unconditionally —
rejected: DD-238 rejected the same for the one-hop case (spoofable when the
hop is not pinned); pinning it to the gateway network is exactly the
correction that makes the header trustworthy. (c) Have Envoy do the
limiting (local rate-limit policy at the edge) — rejected for now:
it forks the limiter from the tested contract (`e2e/config/nginx.conf`,
DD-142/238's pair), and the webapp's allowlist semantics (internal callers
exempt) are geo-based, which the edge would have to re-implement. Recorded
as a 10.5+ candidate if per-edge limiting earns its keep.

**Consequences.** The `realip` placeholder joins the template contract
(the ninth `AURELIUS_ATLAS_WEBAPP_*` name becomes ten); the chart-contract
suite pins the render against both CIDR-list defaults. A GKE overlay names
its alias IP range; a deployment whose Gateway runs outside the pod network
names its own. The server-side setting exists today (`forwarded_allow_ips`,
DD-238); only the rendering is new here.

### DD-262. The webapp nginx config resolves at pod start, not at Helm render

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** The webapp chart ships the nginx config as a ConfigMap of a
chart _asset_ — `helm/files/nginx.conf.template`, a byte-copy of the app's
`nginx.conf.template` (drift-guarded by a byte-compare test) — and a
`resolve-nginx-config` init container (the same webapp image, POSIX `sh` +
`sed`) substitutes the `${AURELIUS_ATLAS_WEBAPP_*}` placeholders from the
container's environment into an emptyDir that nginx reads at
`/etc/nginx/conf.d`. Helm performs no substitution; the image is unchanged
(it ships the raw template and fails loudly at parse, the Dockerfile's
contract). The hardened `dhi.io/nginx` base has neither `envsubst` nor
`bash` — the upstream image's `/docker-entrypoint.d/` 20-envsubst machinery
is not in it — hence the chart-side init container rather than an
entrypoint convention.

**Reason.** The template's ninth placeholder is
`${AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN}` — a _generated_ credential.
Rendering it Helm-side means the chart must expand
`lookup(-collector-legacy)` into the ConfigMap, and that is DD-256's
forbidden shape with a different secret: a Helm-rendered `randAlphaNum`
appearing in both the Secret and a ConfigMap, where `lookup` protects only
the Secret side — a pod rescheduled after a values edit gets yesterday's
bearer baked into its config while the Secret holds today's. Resolving at
pod start from the mounted Secret is the pattern the increment already
runs: Keycloak's realm placeholders resolve inside the process, fed from
the environment the chart fills from the generated Secret (DD-256). The
remaining placeholders (upstream names, resolver, origins, CA path) carry
no secret, but they resolve the same way — one mechanism, one contract,
byte-identical to the e2e stack's config-modulo-values.

**Alternatives.** (a) `tpl`/substitution over the file at render —
rejected: the double-generation race above. (b) Bake a filled config with
`envsubst` at image build — rejected: freezes environment values into the
image (the same environment deploys many clusters; CHT-04). (c) Fork an
nginx image with `envsubst` — rejected: the hardened image exists to not
carry GNU gettext. (d) Ship the template untouched and let nginx fail at
parse — rejected: that is the _bare container's_ deliberate failure, not a
deployable's.

**Consequences.** `tests/test__charts_webapp.py` byte-compares the asset
against `apps/aurelius-atlas-webapp/nginx.conf.template` every run; editing
the template requires re-copying. The init container's `sed` handles
exactly the `AURELIUS_ATLAS_WEBAPP_` name prefix; a template placeholder
outside it resolves to nothing loudly (a `grep` for unresolved `${` fails
the init before nginx starts). Next free DD: 263.

### DD-263. BackendTLSPolicy renders the v1 `caCertificateRefs` list

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** The umbrella's `httproutes.yaml` renders each TLS backend's
`BackendTLSPolicy` at `apiVersion: gateway.networking.k8s.io/v1` with
`validation.caCertificateRefs` — a _list_ of `{group, kind, name}` refs to the
trust CA Secret (which carries `ca.crt`) — plus `validation.hostname` set to
the Service name (SNI and the per-Certificate SAN check). It does not render
the `v1alpha3`/singular-`caCertRef` shape.

**Reason.** The minikube hand check caught the first render server-side
applying as `.spec.validation.caCertRef: field not declared in schema`: the
standard Gateway API CRD bundle (v1.6.1 experimental, installed per the
runbook) declares only the v1 `validation` fields; `v1alpha3` with the
singular ref is not in that schema at all. Envoy Gateway 1.9.3's
`BackendTLSSettings` docs confirm the v1 shape works end to end, including a
single Secret ref with the CA in `ca.crt`. The keycloak round-trip through the
Gateway then completed with the policy Accepted.

**Alternatives.** (a) Install the `gateway.networking.x-k8s.io` experimental
bundle to get `v1alpha3` — rejected: a whole extra CRD set for a field the
stable API already has. (b) Drop CA pinning and trust the proxy's system
store — rejected: CHT-30's whole point is the Gateway verifies the leaf the
same way an in-cluster client does.

**Consequences.** `tests/test__charts_edge.py` pins the apiVersion and the
list form; a future Gateway API upgrade needs no chart change. Next free DD: 264.

### DD-264. The webapp's emptyDirs mount below the image's symlink baked-in paths

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** The webapp chart's writable-path emptyDirs mount at
`/run/nginx`, `/var/lib/nginx/tmp` (not `/var/lib/nginx`), and
`/var/log/nginx`. The chart's nginx-upstream placeholder defaults are cluster
FQDNs (`<svc>.<ns>.svc.cluster.local`) rather than short Service names.

**Reason.** The minikube hand check caught the webapp CrashLooping twice over.
(1) The `dhi.io/nginx` image bakes `/var/lib/nginx/logs` and
`/var/lib/nginx/modules` as symlinks into `/var/log/nginx` and
`/usr/lib/nginx/modules`; an emptyDir over `/var/lib/nginx` hides them, and
`load_module modules/ngx_otel_module.so` then dlopens a path that no longer
exists — nginx exits at boot. Mounting at `/var/lib/nginx/tmp` covers nginx's
only real compiled-in writable need there (the temp dirs) while the image's
own `logs`/`modules` symlinks survive (the `/var/log/nginx` emptyDir still
covers the logs path; `/etc/passwd`'s home is `/home/nginx`, unused). (2) Once
booting, the `/api` leg 502'd: the template's `proxy_pass` is a variable,
which forces nginx's stub `resolver` (the template sets it from
`${..._DNS_RESOLVER}`), and that resolver never applies `resolv.conf`'s
search list — a short name like `atlas-server` fails with `Host not found`.
The peer Certificates carry the `.svc.cluster.local` SAN, so the FQDN default
fixes resolution and keeps `proxy_ssl_name` verification (DD-286) intact.

**Alternatives.** (a) `postStart`/init `ln -s` into the mounted emptyDir —
rejected: the chart would re-enact the image's filesystem contract. (b)
Non-variable `proxy_pass` (static upstream) — rejected: the template is
shared with the compose stack, where the variable form is needed for the
resolver-based OTel leg, and DD-262 keeps chart and compose configs
byte-identical. (c) Values-level FQDN overrides only in
`environments/*.yaml` — rejected: the defaults are the common case and must
work unaided (CHT-04).

**Consequences.** `tests/test__charts_webapp.py` pins the three mountPaths
and the FQDN placeholder defaults. Compose is unaffected (its `nginx.conf`
is static and docker's DNS handles short names there). Next free DD: 265.

### DD-270. The webapp serves TLS behind the gateway: the last plaintext hop closes

- **Status:** Accepted
- **Increment:** 10.3c
- **Date:** 2026-10-29

**Context.** DD-285 shaped the webapp's listener as plaintext behind the
gateway, and `helm/templates/httproutes.yaml` gave it no BackendTLSPolicy.
The trust analysis of the OTel/API flows found the one inversion between the
dev stacks and the cluster: the e2e nginx already listens `8080 ssl` with the
project's mkcert leaf (`apps/aurelius-atlas-webapp/e2e/config/nginx.conf`),
so the shipped chart was weaker than the tested dev shape. From 7.3 the
browser's bearer token and per-user OTLP pushes arrive at the Gateway, whose
HTTPS listener terminates there — and would then cross the gateway→nginx hop
in plaintext, one hop before the same token's TLS-verified `/api/` proxy
(whose comment names exactly that threat). The invariant "user tokens never
cross plaintext" (ADR 039) needs the hop closed before the tokens flow.

**Decision.** The webapp's nginx listener serves TLS: the shipped template
gains `listen 8080 ssl` with `ssl_certificate`/`ssl_certificate_key` from two
new placeholders (the contract grows ten → twelve, CHT-25 amended in place —
PR #159 is still in review). The chart ships a `Certificate` following the
server's pattern (CHT-22: SANs = the Service and its FQDNs, issued by the
umbrella's CA issuer; `tls.certSecretName` brings your own and renders
nothing), mounts the leaf whole beside the trust root, and flips its probes
to HTTPS. The umbrella's `edge.listeners` helper flips the webapp entry's
`tlsBackend` to true, so `httproutes.yaml` renders the third
`BackendTLSPolicy` — CA-pinned via `caCertificateRefs`, SNI = the Service
name = the SAN — with no template change of its own. Grafana stays the lone
plaintext backend (anonymous Viewer, login disabled, DD-267): nothing
secret-bearing crosses its hop, and DD-285's clause stands scoped to it.
DD-285's gateway choice is untouched — this supersedes only its
plaintext-backend clause.

**Alternatives.** (a) Leave it until 7.3 — rejected: the e2e stack already
runs TLS nginx (the cluster should not ship weaker than the test rig), and
landing it beside the auth wiring bundles two unrelated slices. (b) mTLS to
the webapp — rejected: the Gateway API `BackendTLS` validation is
CA-and-SNI; client certificates would need Envoy Gateway BackendAuth policies
for an identity the app layer already carries (DD-285's mesh argument).
(c) Reuse the `<release>-edge-tls` leaf — rejected: its SANs are the browser
hosts, not the Service name; the BackendTLSPolicy hostname check is the
Service name (CHT-22's rule, as for every other backend).

**Consequences.** CHT-23's and CHT-25's rule text in the 10.3a spec amend in
place (unmerged); CHT-30's "plaintext backends (webapp) none" becomes
Grafana-only. The webapp's placeholder count is twelve; the byte-copy drift
guard covers the new template. The probes are HTTPS (kubelet skips
verification — liveness, not trust, DD-260's lesson). A cluster upgrade to
this chart is an atomic umbrella `helm upgrade`: the BackendTLSPolicy and the
TLS listener ship together, so there is no window where Envoy dials TLS into
a plaintext listener or plaintext into a TLS one.
Next free DD: 271.

### DD-294. The minikube trial findings in the aux charts land in 10.3

- **Status:** Accepted
- **Increment:** 10.1 (trial) · fixed in 10.3
- **Date:** 2026-10-28

**Decision.** A trial `helm install` of the umbrella on minikube (the three aux
APIs — the only real workloads 10.1 ships — with locally built images and
self-signed `kubernetes.io/tls` Secrets) surfaced two defects in the aux
charts' rendered Deployments. Neither is fixed in 10.1; both are scheduled
into 10.3, where the app charts get their real workload wiring:

1. **The CA file has no backing store.** The aux charts' default settings env
   points `AUTH_CA_FILE`/`OTEL_CA_FILE` at `/etc/aurelius-atlas/tls/ca.crt`,
   but the TLS volume mounts only a `kubernetes.io/tls` Secret — which carries
   only `tls.crt`/`tls.key` — so a spec-conformant install crash-loops at boot
   on pydantic's `path_not_file`. The `tls.caConfigMap`/`tls.caPath` values the
   charts already declare are dead: the Deployment template never reads them.
   10.3 wires the mount for real — cert-manager issues each service's
   Certificate from the self-signed ClusterIssuer (DD-286) and the issuer's
   `ca.crt` reaches the pod through the declared CA value (Secret or
   ConfigMap), and the settings default and the mount become consistent.
2. **lineage-model cannot boot its own defaults.** `atlas_base_url` and
   `data2model_url` are required settings with no defaults, and the chart
   renders neither, so the rendered Deployment always fails validation. 10.3
   sets them from the in-cluster joins (`https://<server-svc>:21000/`,
   `https://<data2model-svc>:21001/` — the sibling Service the same chart
   renders), the same increment that wires the OTEL endpoints the values
   comments already promise.

**Reason.** 10.1's stated boundary is the foundation: charts render, lint,
version, and publish, and the acceptance gate is render-level (CHT-06). Both
fixes are workload-wiring changes — a trust mount and a settings join — and
the trial shows the aux charts were skipped over by the render gate exactly
where 10.3's scope line already says they get filled in (the three auxiliary
APIs, CHT-20..34). Fixing them under 10.1 would land half the trust model
(no cert-manager yet) and duplicate 10.3's edits.

**Alternatives.** (a) Fix the CA mount now with a plain-Secret `ca.crt` key —
wrong shape: the real CA arrives with cert-manager in 10.3/10.4 and the key
would be re-plumbed. (b) Give the lineage-model settings chart defaults —
wrong owner: those URLs are deployment joins like `AUTH_SERVER_URL`, not
component constants, and deriving them in-chart before the server chart has a
Service (10.3) would be guesswork.

**Consequences.** 10.3's spec must carry both as rules (CA mount for every TLS
app; lineage-model upstream URLs) with render assertions, and its minikube
install must boot the aux Deployments with no out-of-band values — the
`/tmp`-style overrides this trial needed (an extra `ca.crt` in the TLS Secret,
an `extraEnv` file for the two URLs) are the acceptance test's negative space.
The trial itself passed otherwise: install/upgrade reached `deployed`, all
three rollouts went Ready on the HTTPS `/liveness` probes, and the derived
`AUTH_SERVER_URL` matched the overlay domain. Next free DD: 252.

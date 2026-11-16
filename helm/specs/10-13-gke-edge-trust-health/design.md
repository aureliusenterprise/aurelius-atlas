# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md).
Their [rules](../../../docs/architecture/conversion/design-log.md#rules)
still apply: an accepted entry is never edited except its status line, and a
changed decision is a new entry that supersedes the old one.

## Entries

### DD-643. An optional edge issuer moves only the browser leaves to a public CA

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16

**Context.** The chart signs every leaf from one private CA (CHT-29/30). The
rc.3 deployment onto GKE proved both single-issuer postures fail in
practice: with the private CA signing the edge, the browser rejects
`atlas.<domain>` until the operator installs the CA into the trust store by
hand; setting `global.trust.issuerRef` to the cluster's ACME
`ClusterIssuer` instead moves **every** leaf to it, and Let's Encrypt
refuses to issue for `atlas-webapp.atlas.svc.cluster.local` — the whole
internal mTLS mesh (DD-270) fails to get certificates. The two trust
anchors are disjoint by nature: browsers carry a public root set, the mesh
carries the private root.

**Decision.** `global.gateway.edge.issuerRef` (default `""`) names a
separate issuer for the browser leaves only. When set, the edge
Certificate's `issuerRef` and a new companion `<release>-keycloak-edge-tls`
Certificate (public `keycloak.<domain>` SAN only) name it; the keycloak
listener's `certificateRefs` follow through the
`aurelius-atlas.keycloakEdgeSecret` helper, so the keycloak chart keeps
issuing its own SAN-covering internal leaf untouched. The internal
Certificates — server, webapp, keycloak service leaf, postgres, everything
under `global.trust` — stay on the private CA. `edge.certificate.privateKey`
(optionally) pins the leaf key algorithm: Let's Encrypt rate-limits RSA
issuance per registered domain ("too many certificates already issued"),
and the deployment hit it; `ECDSA`/256 clears the limit and every current
browser trusts it (the gke overlay sets it). The stock default (`""`) keeps
cert-manager's RSA 2048 and the exact rc.3 render.

**Alternatives.** (a) Ship the CA to browsers (an operator task outside the
chart; it also pins every client's trust store to a private root for a
public host — the posture a public host should not need). (b) ACME for
everything — rejected: impossible for `.svc.cluster.local` names, as
tested live. (c) Overlay the issuerRef with `--set` on the edge cert only —
rejected: keycloak's leaf comes from the keycloak subchart with no umbrella
hook to patch it, which is why the companion Certificate exists. (d) ECDSA
always — rejected: it changes the stock render's key algorithm for no
stock benefit.

**Consequences.** The gke overlay becomes a plain values file (edge issuer

- ECDSA + health checks) with no manual cluster edits. The cluster's
  ACME `ClusterIssuer` and its DNS-01 solver move from "worked around" to a
  runbook prerequisite (CHT-126). The keycloak host now carries two Secret
  names depending on posture; the helper is the single mapping, and the edge
  test pins both branches.

### DD-644. The backend-CA trust lands in a ConfigMap, synced by a hook Job

- **Status:** Superseded by DD-652 (the ConfigMap pin stands, the sync
  becomes a trust-manager Bundle)

**Context.** `BackendTLSPolicy.validation.caCertificateRefs` tells the
Gateway implementation which root to verify the backends with. rc.3 pinned
the trust CA **Secret** (CHT-30), and GKE's managed Gateway rejected the
policy: `no-valid-refs: no valid certificates found`. Live testing
narrowed the accepted shape: `kind: ConfigMap` with a `ca.crt` key, same
namespace as the policy — a Secret ref never resolves. cert-manager's own
answer is ConfigMap CA injection (`cert-manager.io/inject-ca-from-secret`),
and it does nothing on the cluster's cert-manager 1.9.1 (tested live: the
injected key never appears). The CA itself is the
`aurelius-atlas-selfsigned-ca` Secret (or the BYO `caBundle` Secret) that
cert-manager and the operators own; the chart cannot render its bytes at
template time.

**Decision.** The umbrella renders a `<release>-backend-ca` ConfigMap
(inert `ca.crt: ""` so the policy always has a name to pin) and a
`<release>-ca-sync` hook Job (post-install, post-upgrade;
`before-hook-creation,hook-succeeded`) that copies the live CA PEM in: the
container polls `CA_SOURCE_SECRET` through the Kubernetes API using its
mounted service-account token and the in-cluster CA, then creates or
merge-patches `CA_TARGET_CONFIGMAP`. A dedicated ServiceAccount/Role/
RoleBinding grants get/create/patch/update on configmaps in the release
namespace only. The container is the workspace Python base image
(`dhi.io/python:3.14-alpine3.24`, digest-pinned per CHT-96 — the image has
no `sh`, so the script runs as `python3 -B -c` with the source secret and
target ConfigMap names passed by env), `runAsNonRoot` 65532, read-only root,
all capabilities dropped, small bounded resources. Both render only when
`gateway.enabled` and the chart owns a CA (`createIssuer` or `caBundle`).

**Alternatives.** (a) Upgrade cert-manager for injection — rejected: the
cluster's version is the operator's choice, and injection from a Secret
that is recreated on CA rotation still races the policy. (b) The chart
writes `ca.crt` at template time — impossible: the CA bytes exist only
after install (generate/preserve pattern). (c) An init container on a
workload — rejected: wrong lifecycle, the ConfigMap must exist for policies
that are independent of any one pod. (d) `helm template`-time caBundle
requiring operators to pass the CA — rejected: it breaks the
generate-and-preserve UX the credentials already have.

**Consequences.** CHT-30's Secret ref is superseded by CHT-127. The sync
runs on every upgrade, so CA rotation (cert-manager renews the Secret) is
picked up by the next `helm upgrade` without extra machinery — acceptable
because the self-signed root lives ten years. `dhi.io/python` joins the
pinned third-party set (`conftest.PINNED`, the drift guard). The Job is a
hook: `helm template` output stays inert for offline tests, and a failed
sync surfaces as a hook failure instead of a silently-unverified backend
policy.

### DD-645. HTTPS backend health checks, gated because the kind is implementation-specific

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16

**Context.** Every backend behind the edge serves TLS only (DD-270). GKE's
managed Gateway probes backends over plain HTTP by default, so every probe
against a TLS port fails, the backend group goes UNHEALTHY, and the URL map
substitutes a synthetic `serve500` fault-injection backend — the browser
gets 500s that look like an app failure. The fix on GKE is a
`HealthCheckPolicy` (`networking.gke.io/v1`) naming the backend Service
with `config.type: HTTPS` and an `httpsHealthCheck.requestPath`.

**Decision.** `global.gateway.healthCheck` (default `enabled: false`) turns
on one `HealthCheckPolicy` per TLS-backend listener (atlas, keycloak, and —
when enabled — dashboard; never grafana, whose backend is plaintext,
DD-267). `paths.<listener>` defaults to each backend's existing readiness
path (`/config.json`, `/realms/master`,
`/api/atlas/admin/readiness`) so the gateway asks the same question
readiness already answers; interval/timeout/thresholds are values with the
GKE-validated defaults. When off (the stock render) nothing renders.

**Alternatives.** (a) Always render — rejected: the API kind exists only on
GKE; Envoy Gateway or nginx would reject the unknown resource, and the
stock chart must install anywhere (CHT-29's premise). (b) HTTP probes
against the plaintext grafana path on the TLS services — impossible, the
listeners speak TLS. (c) NodePort/port-forward validation instead —
rejected: this increment's acceptance is exactly the smooth public-host
deployment.

**Consequences.** The GKE overlay enables it; the runbook prerequisite
names the Certificate Manager API (the Gateway implementation refuses
TLS/health-check features without `certificatemanager.googleapis.com`). The
test pins the listener set, apiVersion, HTTPS type, and paths, and pins
that a stock render has none (CHT-128). Other implementations keep their
own mechanisms (Envoy `BackendTrafficPolicy` etc.) — a future increment can
add a per-class translator if a second platform matters.

### DD-646. `appProtocol: HTTPS` on the TLS Service ports

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16

**Context.** The Gateway API's Service import reads `appProtocol` to pick
the protocol it speaks to a backend; GKE's managed Gateway documents it as
the way to say "talk TLS to this port". Without it the import falls back to
`protocol: TCP`, which on GKE pairs with the DD-645 problem to keep the
backend group unhealthy.

**Decision.** The three TLS-only ClusterIP Services — webapp, server,
keycloak — set `appProtocol: HTTPS` on the `https` port. The keycloak
`https-issuer` alias port (same listener, different number, DD-265) and the
headless RSS discovery companion stay as they are; no plaintext Service
(the collector, postgres, elasticsearch, grafana) gains the field.

**Alternatives.** (a) Rely on the BackendTLSPolicy alone — insufficient on
GKE: the policy says _how_ to verify TLS, `appProtocol` says the port _is_
TLS; the deployment needed both. (b) Name-only convention (`https` port
name) — implementations treat it inconsistently, and the standard field
exists exactly for this.

**Consequences.** A stock render changes by one field per Service (CHT-129
pins all three plus the keycloak test's port map). Nothing to configure;
the field describes the existing fact that these ports serve TLS only.

### DD-647. nginx root redirect is relative (`absolute_redirect off`)

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16

**Context.** Visiting `https://atlas.<domain>/` answered
`Location: https://atlas.<domain>:8080/browse`. nginx builds absolute
redirects from the Host header **plus the listening port**, and the webapp
listens on 8080 behind the gateway's 443. The browser takes the port
literally; the load balancer's portmap rewrite (443→8080) covers the
request lane, not a port the redirect re-introduces client-side, so the
redirect leaves the edge (first stuck as a connection failure). Live-fixed
by hotpatching the ConfigMap; recorded here as the chart fix.

**Decision.** The webapp's nginx template (and its byte-copy chart asset,
CHT-24) gains `absolute_redirect off;` in the `server` block, before the
root redirect. `Location: /browse` then resolves against the browser's own
origin.

**Alternatives.** (a) `port_in_redirect off;` — fixes only the port, still
sends an absolute URL built from Host; the relative form is the robust
answer for any proxy topology. (b) `absolute_redirect` per-location —
rejected: every current and future redirect in this server wants the
relative form. (c) `proxy_redirect` at the gateway — out of the chart's
hands, and nginx's own redirect never passes through a proxy body filter.

**Consequences.** One line in the template; the ConfigMap test pins it
above the root-redirect block (CHT-130). The live hotpatch disappears on
upgrade to rc.4 because the chart now ships the same content.

### DD-648. The ca-sync Role may `get` its CA Secret

(Superseded with DD-644 by DD-652: the Role is gone.)

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16

**Context.** The first upgrade through the hook failed. The Job's Role
granted `configmaps` only, so its poll loop could not read the CA Secret
it copies. It retried until the deadline, and the failed post-hook marked
the whole release failed. The Secret read was missing from the
least-privilege list, which was written around the output and not the
input.

**Decision.** The Role gains `{secrets: [get]}` beside
`{configmaps: [get, create, patch, update]}`. The test pins both rules.

**Alternatives.** (a) Mount the CA Secret into the Job: rejected, because
the secret appears about 90 s after the hook starts, and a mount fixed at
pod creation cannot follow cert-manager issuing it. (b) Read the ConfigMap
through the mounted service-account token against an escalated role:
rejected, it widens the permission instead of naming the one read.

**Consequences.** The hook finishes in seconds once the CA exists. The
permission is narrow: it reads one secret class in the edge namespace.

### DD-649. `volumeClaimTemplates` carry version-free labels

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16

**Context.** The upgrade refused to apply the elasticsearch StatefulSet:
"`volumeClaimTemplates: Invalid value: field can not be updated`". The
claim template carried the full label set, `helm.sh/chart` and
`app.kubernetes.io/version` included, so every release changed a field
Kubernetes freezes after the first install. That locked out every upgrade
after rc.3. The keycloak-postgres template always used selector labels
only and never hit this.

**Decision.** The claim template labels are the selector labels plus
`app.kubernetes.io/component`.

**Alternatives.** (a) Keep the versioned labels and delete then recreate
the StatefulSet each upgrade: rejected, that is the move this increment
exists to remove. Selector labels plus the component label match the
working precedent, and a PVC made from the claim keeps a stable identity,
which is what a storage object wants.

**Consequences.** The chart upgrades in place. A PVC made at install
never looks like it belongs to one release.

### DD-650. The cosign attest and sign targets run serially too

- **Status:** Proposed
- **Increment:** 10.13 (a fix, 2026-11-16)
- **Date:** 2026-11-16
- **Related:** DD-641

**Context.** DD-641 serialized only the two verify targets, so the publish
chain still fanned `docker-attest`, `docker-sign`, and `helm-sign` out
across ten projects at once. Each cosign call touches a resource the
runner shares, and the burst broke it two ways. The TUF root fetch failed
to persist its cache metadata ("failed to persist metadata", tag
`v0.1.0-rc.4` and `v0.1.0-rc.5` first attempts). After a rerun, the same
step failed differently: ten parallel `cosign attest` calls requested an
ambient OIDC token at once and the Actions token service answered one of
them with a non-JSON body ("invalid character 'u' looking for beginning
of value", `v0.1.0-rc.5` second attempt). Both faults killed the sign
step while the images themselves published fine.

**Decision.** `docker-attest`, `docker-sign`, and `helm-sign` carry
`parallelism: false`, the flag DD-641 gave the verify pair. Nx runs each
cosign call alone, so the runner fetches the TUF root and the OIDC token
one at a time. Only these targets change. The build, publish, and scan
fan-out stay parallel.

**Alternatives.** (a) Retry the failed step by hand, as rc.4 and rc.5 both
needed: rejected, it treats the symptom and every release repeats it.
(b) Add a retry loop around each cosign command: rejected, it hides a
race that serialization removes outright, and a retry on the OIDC token
still races the same endpoint. (c) Serialize the whole `run-many` in
`nx.json`: rejected, it slows the many independent build and publish
tasks for a fault only the cosign pair has.

**Consequences.** The publish sign step is deterministic. The signing work
runs serially, which the earlier verify serialization already proved is
cheap next to the build it follows. A future cosign target copies this
flag for the same reason.

### DD-651. The edge issuer makes split-horizon DNS load-bearing

- **Status:** Proposed
- **Increment:** 10.13 (a runbook finding, 2026-11-16)
- **Date:** 2026-11-16
- **Related:** DD-265, DD-643

**Context.** In-cluster consumers reach the issuer by its public name, and
that name resolved to the load balancer, so each one hairpinned out through
the gateway. With one private CA, the gateway answered with a private leaf,
so a consumer pinned to that CA accepted it and DD-265's missing DNS entry
stayed invisible. The edge split (DD-643) moved the gateway's browser leaf
to a public CA, so the same hairpin now returns a public leaf. Every
consumer still pinned to the private CA failed with `x509: certificate
signed by unknown authority`: the collector's OIDC extension crashed, the
apps' and pullers' ingest mints sent telemetry headerless, and login could
not fetch the issuer's keys. The atlas-dev reinstall surfaced all three at
once.

**Decision.** Keep the shipped pins and supply DD-265's split-horizon entry,
so the issuer name resolves to the Keycloak Service inside the cluster. The
Service answers the public name over its CA-pinned 443 listener, its leaf
carries the public host in its SANs, and the request keeps the public Host,
so every token keeps the canonical `iss`. No chart change. On GKE the
mechanism is a private Cloud DNS zone scoped to the cluster network: this
cluster's kube-dns ConfigMap is empty and pods dial the hosted resolver, so
a CoreDNS rewrite does not reach them.

**Alternatives.** (a) Drop the private-CA pin in the issuer-touching
components when an edge issuer is set, so they use the image's system trust
(the Let's Encrypt root). The collector proved this works, but the job image
carries no system roots, the puller images are unknown, and it still sends
internal issuer traffic out through the public gateway. Rejected. (b) Point
`global.issuer.url` at the in-cluster Service name. Rejected: DD-265 chose a
DNS entry so the Host and `iss` stay the public name with no per-cluster
value, and a Service host is the wrong issuer identity.

**Consequences.** Split-horizon DNS becomes a hard prerequisite whenever an
edge issuer is set, not only when observability runs. The runbook gains the
GKE private-zone recipe, with the one sharp edge: a private zone is
authoritative for the whole apex in-cluster, so every other host under it
(atlas, and any future one) needs a record too, else it returns no answer.

### DD-652. The backend-CA sync is a trust-manager Bundle, not a hook Job

- **Status:** Proposed
- **Increment:** 10.13
- **Date:** 2026-11-16
- **Related:** Supersedes DD-644 (and DD-648 with it); relies on DD-259,
  DD-286

**Context.** DD-644 carried the CA PEM from the Secret to the ConfigMap
with a hook Job: five chart objects (ConfigMap, ServiceAccount, Role,
RoleBinding, Job), a digest-pinned Python image, an embedded `python3 -c`
script, and the widened RBAC DD-648 needed. It runs only at install and
upgrade, so a CA change between releases waits for the next
`helm upgrade`. cert-manager names the supported mechanism for exactly
this hop: its trust docs tell a `BackendTLSPolicy` consumer to "point those
fields at a trust-manager `Bundle` target", and a `Bundle` names a source
Secret and keeps a same-named target ConfigMap in sync continuously.

**Decision.** The umbrella renders one cluster-scoped `Bundle`
(`trust.cert-manager.io/v1alpha1`) named `<release>-backend-ca` instead of
the five objects. Its source is the CA Secret's `ca.crt` key; its target is
the same-named ConfigMap, which the trust-manager controller creates and
owns. Two API facts shape the render. An empty `namespaceSelector` syncs
the target to every namespace, so the Bundle pins it with
`matchLabels: {kubernetes.io/metadata.name: <namespace>}`. Sources are read
only from trust-manager's configured trust namespace, so the runbook
installs trust-manager with `app.trust.namespace` set to the release
namespace (which must exist first). The chart stops rendering the
ConfigMap: the controller owns it, and a chart-owned copy fights the owned
copy on every upgrade. Gate and name stay as DD-644 set them. The
`dhi.io/python` pin leaves the umbrella's values, and `conftest.PINNED`
with it: the committed-pin map drops to thirteen triples, the stock
umbrella render to eight third-party images.

**Alternatives.** (a) Keep the Job — rejected: the Bundle is smaller,
declarative, rotation-continuous, and the supported path. The Job earns
its keep only on clusters that refuse a second prerequisite, and the chart
already names cert-manager as one. (b) cert-manager cainjector —
impossible: it injects only `caBundle` on webhook-registry kinds, never a
ConfigMap. (c) `wellKnownCACertificates: System` on the policy — wrong for
a private-CA backend. (d) Point the Bundle straight at the CA Secret (the
docs' "intentionally copying" section suggests a dedicated intermediate
source for root rotation) — rejected for now: the self-signed root lives
ten years and every leaf rotates with it, so a copy step guards a rotation
the trust model does not have. Revisit if root rotation ever goes live.

**Consequences.** trust-manager joins the runbook prerequisite list next to
cert-manager, which breaks both stock posture paths (minikube and GKE) until
the cluster carries it — accepted deliberately, per the owner's
architecture call. The `conftest.PINNED` map and the digest guard lose
`dhi.io/python` (it stays pinned in the app charts). The install hook
machinery, its RBAC, and its image supply all disappear. A chart-owned
`<release>-backend-ca` ConfigMap from an rc.6-or-earlier release is
replaced by the controller-owned copy on the first upgrade (an ownership
label change, not an outage — the policy pin is unchanged).

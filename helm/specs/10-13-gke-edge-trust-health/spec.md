# 10.13 GKE-ready edge: split browser trust, backend-CA sync, backend health checks

- **Status:** in review
- **Pull request:** (this PR)
- **Records:** DD-643..647 (adds), DD-265/DD-270 (relies
  on: the TLS backends), DD-278 (relies on: the digest-pinned image),
  CHT-29/30 (supersedes parts: the single-issuer edge, the Secret CA ref)

## Scope

The first real deployment of the published chart (rc.3) onto GKE
(`atlas-dev`) surfaced three stacked blockers between the chart's rendered
posture and what a managed Gateway implementation accepts, plus two smaller
ones found while validating the hosts. Each one was fixed live on the
cluster first, then baked into the chart here, so the next release installs
the validated posture with no manual cluster edits:

1. **Browser trust vs. internal trust.** The chart signs every leaf —
   browser-facing and internal — from one private CA (CHT-29/30). A browser
   does not trust that CA, so the public hosts failed the TLS handshake
   until someone installed the CA by hand. Let's Encrypt cannot sign the
   internal names (`*.svc.cluster.local`), so one ACME issuer for everything
   breaks the mTLS mesh instead. This increment splits the two:
   `global.gateway.edge.issuerRef` moves **only** the browser leaves (the
   edge Certificate and the keycloak browser leaf) to a separate issuer,
   while the internal Service leaves stay on the private CA (DD-643).
2. **BackendTLSPolicy CA reference.** A `BackendTLSPolicy`
   (`caCertificateRefs`) that names a Secret is rejected by GKE's managed
   Gateway ("no-valid-refs: no valid certificates found"): the
   implementation only reads a **ConfigMap** (`ca.crt`, same namespace)
   (DD-644). cert-manager's CA injection into ConfigMaps does not
   work at the cluster's version (tested live). The chart now renders a
   `<release>-backend-ca` ConfigMap and a small post-install/post-upgrade
   hook Job that copies the CA Secret's `ca.crt` into it, and the
   BackendTLSPolicies pin the ConfigMap.
3. **HTTPS backends read unhealthy.** The managed Gateway probes backends
   with plain HTTP; against these TLS-only backends (DD-270) every probe
   fails, and the load balancer serves 500s from a synthetic failure
   backend instead of routing (DD-645). The chart now renders the
   implementation's `HealthCheckPolicy` (HTTPS type, per-listener request
   path) per TLS backend when `global.gateway.healthCheck.enabled` is true.
   The kind is implementation-specific, so it stays off by default.
4. **Wire protocol on the TLS Services.** The Gateway reads `appProtocol`
   on the Service port to pick the backend wire protocol (DD-646).
   The webapp, server, and keycloak ClusterIP Services now set
   `appProtocol: HTTPS` on the https port.
5. **Redirect port leak.** nginx's default absolute redirect bakes the
   container port into `Location` (`https://atlas.<domain>:8080/browse`);
   the gateway's portmap rewrite cannot fix it browser-side (DD-647).
   The webapp's nginx template gains `absolute_redirect off;`.

This increment does **not** deliver: the GatewayClass or the ACME issuer
themselves (cluster prerequisites, runbook §0 — an ACME DNS-01
`ClusterIssuer` plus public DNS for every enabled browser host is the
operator's), per-implementation health-check translation for Gateways
other than GKE's (the values knob exists; only the GKE CRD renders), or
change to the default (private-CA-everything) posture — a stock render is
byte-identical to rc.3 except the `appProtocol` field and the inert
`<release>-backend-ca` ConfigMap.

## Semantics

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-126 | When `global.gateway.edge.issuerRef.name` is set, the browser leaves come from that issuer and the internal leaves do not move: the edge Certificate (and its `privateKey` block when `edge.certificate.privateKey.algorithm` is set) and the companion `<release>-keycloak-edge-tls` Certificate (public SAN only, same issuer) name the edge issuer; the keycloak listener's `certificateRefs` switch to the companion Secret via the `aurelius-atlas.keycloakEdgeSecret` helper; the server/webapp/keycloak internal Certificates keep `global.trust.issuerRef` and their Secrets. Unset (default): no companion Certificate, every leaf keeps the trust issuer — stock render unchanged.                                                                                                                                                                                                                                                  |
| CHT-127 | Every `BackendTLSPolicy` pins `caCertificateRefs` to the `<release>-backend-ca` ConfigMap (`group: ""`, `kind: ConfigMap`, same namespace) — never a Secret. The umbrella renders that ConfigMap (inert `ca.crt: ""` on its own) plus the `<release>-ca-sync` ServiceAccount/Role/RoleBinding/Job when the gateway is enabled and the chart owns a CA (`createIssuer` or a BYO `caBundle`); the Job runs post-install/post-upgrade as a hook (`before-hook-creation,hook-succeeded` deletion), polls the CA Secret named by `CA_SOURCE_SECRET` through the Kubernetes API with its mounted SA token, and merge-patches the `ca.crt` key into `CA_TARGET_CONFIGMAP`. The Job container is the digest-pinned `dhi.io/python` image (CHT-96), `runAsNonRoot` 65532, read-only root, drops all capabilities; the Role grants get/create/patch/update on configmaps in the release namespace only. Gateway off: neither ConfigMap nor Job renders. |
| CHT-128 | When `global.gateway.healthCheck.enabled` is true, the umbrella renders one `HealthCheckPolicy` (`networking.gke.io/v1`) per TLS-backend listener (atlas, keycloak, dashboard — never grafana, whose backend is plaintext, DD-267): `spec.default.config.type: HTTPS`, `httpsHealthCheck.requestPath` from `gateway.healthCheck.paths.<listener>`, and the interval/timeout/threshold values from `gateway.healthCheck`. The `targetRef` is the backend Service in the release namespace. Disabled (default, because the kind is GKE-specific): none render.                                                                                                                                                                                                                                                                                                                                                                                  |
| CHT-129 | The webapp, server, and keycloak ClusterIP Services declare `appProtocol: HTTPS` on the `https` port (the port serves TLS only, DD-270). The keycloak `https-issuer` alias (DD-265) and the headless RSS companion stay without `appProtocol`; no plaintext Service gains it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| CHT-130 | The webapp nginx template carries `absolute_redirect off;` before the root redirect block, so `Location` on the `/` redirect is relative (`/browse`) and never names the container port. The chart asset stays a byte-copy of the app template (CHT-24).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Java origin

Not a port. The rules are deployment posture; Apache Atlas 2.4.0 deploys
behind a hand-configured Jetty/LB with no equivalent artefacts.

## Deviations

No Atlas deviation — this is chart-internal. Against the chart's own
earlier records: CHT-30's "BackendTLSPolicy pinned to the trust root
Secret" is superseded by CHT-127 (ConfigMap + sync Job), and CHT-29's
single-issuer browser Certificate is extended by CHT-126 (optional edge
issuer). Both changes land as new records; the 10.3 spec text stays as
written (records are the history).

## Acceptance

`tests/test__charts_edge.py` — `test__backend_tls_policies_pin_the_trusted_ca`
(CHT-30+127), `test__backend_ca_configmap_and_sync_job_render` (CHT-127),
`test__edge_issuer_splits_browser_trust_from_internal` (CHT-126, renders the
GKE environment overlay), `test__health_check_policies_cover_the_tls_backends`
(CHT-128); `tests/test__charts_webapp.py` —
`test__tls_service_and_https_probes` (CHT-129),
`test__root_redirect_is_relative` (CHT-130); `tests/test__charts_server.py` —
`test__deployment_and_https_service` (CHT-129); `tests/test__charts_keycloak.py`
— `test__service_answers_the_https_standard_port` (CHT-129). Offline:
`uv run pytest tests/test__chart*.py -q --no-cov`. On-cluster: the rc.4
redeploy of `helm/environments/gke.yaml` onto `atlas-dev` must go green with
zero manual `kubectl edit`/`patch` steps (the acceptance for the whole
increment — "iterate until the deployment is smooth").

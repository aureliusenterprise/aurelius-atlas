# Deployment runbook

> [!NOTE]
> **The sequence below is scripted** for minikube:
> `tools/cluster/install.sh up|status|down` (10.5) converges §0–1 —
> prereqs, images, install, and the stuck-release recovery — idempotently.
> The prose stays the reference for what the script does and for clusters
> that are not minikube.

Install Aurelius Atlas into a Kubernetes cluster. The system's shape and the
reasoning behind it are in the [deployment reference](index.md); this page is
the sequence to run.

## 0. Prerequisites

- **kubectl** + a cluster context. Minikube: start it and run
  `minikube tunnel` in a second terminal (the Gateway gets an external IP
  through it); add `atlas.test`, `keycloak.atlas.test` (and
  `dashboard.atlas.test`, `grafana.atlas.test` if enabled) to `/etc/hosts`
  pointing at `127.0.0.1`.
- **cert-manager** installed (CRDs + controller):

    ```bash
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
    ```

- **A GatewayClass** matching `global.gateway.className` (default `envoy-gateway`):

    ```bash
    # minikube (Envoy Gateway). The EG chart installs the controller and the
    # Gateway API CRDs but ships NO GatewayClass — create one:
    helm install eg oci://docker.io/envoyproxy/gateway-helm --version 1.9.3 \
        -n envoy-gateway-system --create-namespace
    kubectl apply -f - <<'EOF'
    apiVersion: gateway.networking.k8s.io/v1
    kind: GatewayClass
    metadata:
        name: envoy-gateway
    spec:
        controllerName: gateway.envoyproxy.io/gatewayclass-controller
    EOF
    ```

- **Pull secrets** (private registries) in the target namespace:

    ```bash
    kubectl create namespace atlas
    kubectl create secret docker-registry dhi-pull \
        --docker-server=dhi.io --docker-username=<user> --docker-password=<token> -n atlas
    kubectl create secret docker-registry ghcr-pull \
        --docker-server=ghcr.io --docker-username=<gh-user> --docker-password=<gh-pat> -n atlas
    ```

- **The issuer decision is permanent.** The Keycloak issuer URL derives from
  `global.domain` and tokens embed it; changing it after entities exist
  invalidates every token. Choose the domain at first install.

- **Split-horizon DNS for the issuer** (DD-265, with `atlas-observability`
  enabled): in-cluster producers (the collector's OIDC validator, the apps'
  OTLP mints, the store pullers) reach the issuer over its **public** name —
  `keycloak.<domain>` — so that name must resolve to the Keycloak Service
  inside the cluster too (the cluster port of the dev stack's per-producer
  `extra_hosts`). A real deployment's DNS usually does this already:
  `atlas.test` is your domain, and its internal view points at the cluster.
  On a dev cluster, give CoreDNS the entry:

    ```bash
    # minikube: add a `rewrite name` stanza to the Corefile
    kubectl -n kube-system edit configmap coredns
    ```

    ```text
    # inside the `Corefile:` data, beside the `kubernetes` block:
    rewrite stop name keycloak.atlas.test atlas-keycloak.atlas.svc.cluster.local
    ```

    Then `kubectl -n kube-system rollout restart deployment coredns`. The
    Keycloak Service answers the public URL's implicit port (it serves 443
    beside 8443, CHT-41), and the request's Host stays the public name, so
    every token keeps the canonical `iss` whichever horizon it dials from.
    Verify both horizons after install:

    ```bash
    kubectl -n atlas run mint-probe --rm -i --restart=Never --image=curlimages/curl -- \
      -s -k "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token" \
      -d grant_type=client_credentials -d client_id=otel-atlas-server \
      -d client_secret="$(kubectl -n atlas get secret atlas-otel-clients -o jsonpath='{.data.otel-atlas-server}' | base64 -d)" | tr ',' '\n' | grep -A1 '"iss"'
    ```

    The `iss` must be `https://keycloak.atlas.test/realms/aurelius-atlas` — no
    port, no Service name. (`aurelius-atlas` is `global.realm`'s default — the
    hardened realm the chart imports, DD-273. Like the issuer hostname, the
    realm name is first-boot-immutable: Keycloak pins the realm's issuer when
    it creates the realm, so `global.realm` must be final before the first
    install; renaming it later needs a realm rebuild. `master` is the dev
    escape hatch, not a cluster default.)

## 1. Install

```bash
helm install atlas oci://ghcr.io/aureliusenterprise/charts/aurelius-atlas \
    --version <chart-version> \
    -f helm/environments/minikube.yaml \
    --namespace atlas
```

(10.4 replaces the registry URL with the published chart; until then,
`helm install atlas helm -f …` from a checkout, after
`helm dep update helm`.)

Before installing a version, verify the chart artifact carries this
project's publish-workflow signature (CHT-95 — the same keyless identity
the release's images carry):

```bash
cosign verify ghcr.io/aureliusenterprise/charts/aurelius-atlas:<chart-version> \
    --certificate-identity-regexp '^https://github\.com/aureliusenterprise/aurelius-atlas/\.github/workflows/publish\.yaml@' \
    --certificate-oidc-issuer-regexp '^https://token\.actions\.githubusercontent\.com$'
```

What that attests, and what pins bytes (CHT-92..94): the published chart's
nine third-party images (Keycloak, Postgres, Elasticsearch, Prometheus,
Loki, Tempo, Grafana, the collector, curl) are digest-pinned inside it, so
an install pulls exactly those manifests. Aurelius images stay
tag-referenced (`:<release>` tags written only by the signed publish chain)
— the chart signature names the release, and the chart version itself is
immutable in the registry. An operator who wants to freeze one own image
to a digest can set its `image.digest` (e.g. `atlas-server.image.digest=
sha256:<hex>`); the field exists for that, and a set digest always wins
over the tag. Enforcing signatures **at admission** (a cluster policy
rejecting unverified images) is deliberately left to the operator: the
mechanism is cluster posture, not chart content.

The umbrella generates the credentials (Elasticsearch password, Keycloak
admin/DB passwords, the OTel ingest client secrets, legacy token) at first
install and preserves them across upgrades; retrieve them with
`kubectl get secret`. On the hardened realm, `<release>-otel-clients`
carries **one key per ingest client** — `otel-atlas-server`,
`otel-data2model`, `otel-elasticsearch`, `otel-keycloak`,
`otel-lineage-model`, `otel-postgres`, `otel-validate-entity` (CHT-88,
DD-277) — each generated and preserved independently; `master` keeps the
single shared `OTEL_INGEST_CLIENT_SECRET` key. To rotate one leaked
producer's credential, supply its new value and upgrade
(`--set secrets.otelClients.clients.<client-id>=<secret>` or its
`clients:` values entry), then re-import the realm or reset that one
client's secret in the Keycloak console (the import applies at first boot
only) and restart the producer — the other six clients are untouched
either way, which is the point of the per-client shape.

> [!WARNING]
> With `--wait` (or `--atomic`), a workload that never reaches Ready — a
> crash-loop, a Secret the chart expects but nobody created — burns the full
> `--timeout` and leaves the release stuck at `pending-install`; every later
> `helm upgrade` then fails with "another operation … is in progress" until
> `helm uninstall atlas -n atlas` clears it (DD-252). Fix the cause (check
> `kubectl -n atlas get pods` / `helm history atlas -n atlas`), then
> uninstall and reinstall — do not wait the release out.

## 2. Validate

```bash
kubectl -n atlas get pods                          # all Running/Completed
kubectl -n atlas get gateway,gatewayclass,httproute
curl -k https://atlas.<domain>/api/atlas/admin/liveness
curl -k https://keycloak.<domain>/realms/aurelius-atlas    # issuer reachable
```

(The 10.5 POC runs the server's own e2e suite against this install —
`ATLAS_E2E_TARGET=cluster uv run pytest apps/aurelius-atlas-server/e2e`,
after `tools/cluster/install.sh up`; see the [10.5 spec](../conversion/increments/10-5-cluster-validation.md).)

### Grafana

Grafana has no anonymous access: the login screen's **Keycloak** button goes
to the `aurelius-atlas` realm (CHT-84, DD-275). Any realm user lands as
**Viewer**; grant the `grafana` client's `editor` or `admin` client role in
the Keycloak console to escalate (CHT-85). The default access path is a
port-forward, and it works end-to-end — the client registers
`http://localhost:3000/login/generic_oauth` and Grafana's root URL is
request-derived (DD-276):

```bash
kubectl -n atlas port-forward deploy/atlas-observability-grafana 3000:3000
# then open http://localhost:3000 and log in with Keycloak
```

With `global.hosts.grafana.enabled=true` the same login answers at
`https://grafana.<domain>` (the edge route is already wired). The generated
local admin (`<release>-grafana-admin`, keys `user`/`password` via
`kubectl get secret`) is the account-recovery credential — use it only when
the realm path is broken. Keycloak's 8443 NetworkPolicy admits Grafana for
the token exchange (CHT-86); if the login redirects but never completes,
check that hop first.

## 3. Upgrade

```bash
helm upgrade atlas oci://ghcr.io/aureliusenterprise/charts/aurelius-atlas \
    --version <chart-version> \
    -f helm/environments/<env>.yaml \
    --namespace atlas
```

## 4. Uninstall

```bash
helm uninstall atlas -n atlas
```

The Elasticsearch and Keycloak data volumes survive (the PVCs are not owned
by the release); delete them deliberately — see the backup duties in
ADR 026.

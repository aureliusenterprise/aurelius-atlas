# Deployment runbook

> [!WARNING]
> **Skeleton (increment 10.1).** The charts in this tree render and lint in
> CI, and their workloads land in increments 10.2–10.3; the install steps
> below are the shape the runbook will take, and the publish + validated
> install arrive in 10.4–10.5. Do not follow this against production.

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
      -s -k "https://keycloak.atlas.test/realms/master/protocol/openid-connect/token" \
      -d grant_type=client_credentials -d client_id=otel-atlas-server \
      -d client_secret="$(kubectl -n atlas get secret atlas-otel-clients -o jsonpath='{.data.OTEL_INGEST_CLIENT_SECRET}' | base64 -d)" | tr ',' '\n' | grep -A1 '"iss"'
    ```

    The `iss` must be `https://keycloak.atlas.test/realms/master` — no port,
    no Service name.

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

The umbrella generates the credentials (Elasticsearch password, Keycloak
admin/DB passwords, OTel ingest secret, legacy token) at first install and
preserves them across upgrades; retrieve them with `kubectl get secret`.

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
curl -k https://keycloak.<domain>/realms/master    # issuer reachable
```

(The full smoke suite — login, entity write/read, lineage, telemetry — lands
with increment 10.5.)

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

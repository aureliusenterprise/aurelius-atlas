# Deployment runbook

Install Aurelius Atlas into a Kubernetes cluster. The system's shape and the reasoning behind it are in the [deployment reference](<https://aureliusenterprise.github.io/feat-12-9-demo-quality-scores/architecture/deployment/index.md>); this page is the sequence to run, including every DNS, certificate, and rename edge. For the shorter guided path, see [Deploy to Kubernetes](<https://aureliusenterprise.github.io/feat-12-9-demo-quality-scores/user-guide/deployment/index.md>) in the user guide.

## 0\. Prerequisites

- **kubectl** + a cluster context. Minikube: start it and run `minikube tunnel` in a second terminal (the Gateway gets an external IP through it); add `atlas.test` (the product), `auth.atlas.test` (and `dashboard.atlas.test`, `observability.atlas.test` if enabled) to `/etc/hosts` pointing at `127.0.0.1` (CHT-135, ADR 069).
- **cert-manager** installed (CRDs + controller):

  ```
  kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
  ```
- **A GatewayClass** matching `global.gateway.className` (default `envoy-gateway`):

  ```
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
- **A public ACME issuer for a public edge** (10.13, DD-643). The chart signs every certificate from its private CA by default, and a browser does not trust that CA. When the edge serves hosts the public internet visits, set `global.gateway.edge.issuerRef` to a cluster issuer the browsers already trust. Before the first install of that posture: enable your cluster's managed-Gateway TLS APIs (on GKE, the Certificate Manager API — the Gateway refuses TLS and health-check features without it); create a DNS-01 `ClusterIssuer` (Let's Encrypt needs public DNS for every enabled browser host — `app`, `auth`, and any `dashboard` or `o11y` host); and set `global.gateway.healthCheck.enabled=true` on GKE, where the plain-HTTP default probe never passes a TLS-only backend. The overlay `helm/environments/gke.yaml` sets all three. A stock or on-cluster CA deployment needs none of this.

  ```
  # GKE: the APIs a TLS edge needs beyond Gateway itself.
  gcloud services enable certificatemanager.googleapis.com
  ```

  > **Warning**

  **cert-manager must solve DNS-01 against public DNS.** On a cluster with split-horizon DNS (a private zone that shadows your public domain), the controller's default resolver asks the private zone and never sees the `_acme-challenge` TXT record, so every public leaf stays `Pending` with no error past "presented". Patch the deployment before the first ACME issuance:

  ````
  ```bash
  kubectl -n cert-manager patch deploy cert-manager --type merge -p '
  spec:
      template:
          spec:
              containers:
                  - name: controller
                    args:
                        - /app/cert-manager
                        - --dns01-recursive-nameservers=8.8.8.8:53,1.1.1.1:53
                        - --dns01-recursive-nameservers-only'
  ```

  The flag pair is cluster-wide, applies to every ACME issuer, and is
  not part of any chart here (10.14, live-proven on `atlas-dev`).
  ````
- **Pull secrets** (private registries) in the target namespace:

  ```
  kubectl create namespace atlas
  kubectl create secret docker-registry dhi-pull \
      --docker-server=dhi.io --docker-username=<user> --docker-password=<token> -n atlas
  kubectl create secret docker-registry ghcr-pull \
      --docker-server=ghcr.io --docker-username=<gh-user> --docker-password=<gh-pat> -n atlas
  ```
- **trust-manager** (DD-652, with the gateway on — the default): the backend-CA sync. The chart renders one `Bundle` per release, and the trust-manager controller copies the CA Secret into the ConfigMap the BackendTLSPolicies pin. Install it with its **trust namespace** set to the namespace the system installs into — trust-manager reads Bundle sources only from that one namespace, and the namespace must exist before the install:

  ```
  kubectl create namespace atlas --dry-run=client -o yaml | kubectl apply -f -
  helm upgrade --install trust-manager \
      oci://quay.io/jetstack/charts/trust-manager \
      --namespace cert-manager --create-namespace \
      --set app.trust.namespace=atlas --wait
  ```

  Its webhook certificate comes from the cert-manager already installed above. Without this controller, `helm install` of the umbrella fails on the missing `Bundle` CRD — install it before the first install, and before any upgrade of a release older than the switch.
- **The issuer decision is permanent.** The Keycloak issuer URL derives from `global.domain` and tokens embed it; changing it after entities exist invalidates every token. Choose the domain at first install.
- **Split-horizon DNS for the issuer** (DD-265, with `atlas-observability` enabled): in-cluster producers (the collector's OIDC validator, the apps' OTLP mints, the store pullers) reach the issuer over its **public** name — `auth.<domain>` — so that name must resolve to the Keycloak Service inside the cluster too (the cluster port of the dev stack's per-producer `extra_hosts`). A real deployment's DNS usually does this already: `atlas.test` is your domain, and its internal view points at the cluster. On a dev cluster, give CoreDNS the entry:

  ```
  # minikube: add a `rewrite name` stanza to the Corefile
  kubectl -n kube-system edit configmap coredns
  ```

  ```
  # inside the `Corefile:` data, beside the `kubernetes` block:
  rewrite stop name auth.atlas.test atlas-keycloak.atlas.svc.cluster.local
  ```

  Then `kubectl -n kube-system rollout restart deployment coredns`. The Keycloak Service answers the public URL's implicit port (it serves 443 beside 8443, CHT-41), and the request's Host stays the public name, so every token keeps the canonical `iss` whichever horizon it dials from.

  On GKE with the hosted (RUN) resolver, the `kube-dns` ConfigMap is empty and pods dial the VPC resolver, so a CoreDNS rewrite never reaches them. Give the VPC a split view with a private Cloud DNS zone instead (DD-651). `gcloud` names the cluster network with `--networks`:

  ```
  gcloud dns managed-zones create atlas-internal \
      --dns-name=<domain>. --visibility=private --networks=<vpc-network>
  gcloud dns record-sets create auth.<domain>. --zone=atlas-internal \
      --type=A --rrdatas=<keycloak-service-cluster-ip> --ttl=60
  ```

  The private zone is authoritative for the whole apex in-cluster, so every other host under it needs a record too, or it answers nothing. Add the webapp host and a catch-all pointing at the Gateway IP (browsers keep the public view; only pods in the network see this one):

  ```
  gcloud dns record-sets create <domain>. --zone=atlas-internal \
      --type=A --rrdatas=<gateway-ip> --ttl=300
  gcloud dns record-sets create "*.<domain>." --zone=atlas-internal \
      --type=A --rrdatas=<gateway-ip> --ttl=300
  ```

  A `helm upgrade` keeps these records: they are cluster DNS, not release objects. Read the Keycloak Service ClusterIP and the Gateway address from the running release before you create the records. A reinstall does not keep them: a fresh Gateway takes a freshly allocated global IP, and a recreated Service takes a new ClusterIP, so every record must be updated to the new pair (a stalled `issuer-wait` init container is the in-cluster symptom of the stale ones). This entry is a hard prerequisite whenever `global.gateway.edge.issuerRef` is set, because the public edge leaf then breaks a private-CA pin across the load balancer (DD-651).

  Verify both horizons after install:

  ```
  kubectl -n atlas run mint-probe --rm -i --restart=Never --image=curlimages/curl -- \
    -s -k "https://auth.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token" \
    -d grant_type=client_credentials -d client_id=otel-atlas-server \
    -d client_secret="$(kubectl -n atlas get secret atlas-otel-clients -o jsonpath='{.data.otel-atlas-server}' | base64 -d)" | tr ',' '\n' | grep -A1 '"iss"'
  ```

  The `iss` must be `https://auth.atlas.test/realms/aurelius-atlas` — no port, no Service name. (`aurelius-atlas` is `global.realm`'s default — the hardened realm the chart imports, DD-273. Like the issuer hostname, the realm name is first-boot-immutable: Keycloak pins the realm's issuer when it creates the realm, so `global.realm` must be final before the first install; renaming it later needs a realm rebuild. `master` is the dev escape hatch, not a cluster default.)

## 1\. Install

```
helm install atlas oci://ghcr.io/aureliusenterprise/charts/aurelius-atlas \
    --version <chart-version> \
    -f helm/environments/minikube.yaml \
    --namespace atlas
```

From a repository checkout instead of the registry, resolve the component charts first, then install the local chart: `helm dep update helm`, followed by `helm install atlas helm -f …`.

Before installing a version, verify the chart artifact carries this project's publish-workflow signature (CHT-95 — the same keyless identity the release's images carry):

```
cosign verify ghcr.io/aureliusenterprise/charts/aurelius-atlas:<chart-version> \
    --certificate-identity-regexp '^https://github\.com/aureliusenterprise/aurelius-atlas/\.github/workflows/publish\.yaml@' \
    --certificate-oidc-issuer-regexp '^https://token\.actions\.githubusercontent\.com$'
```

What that attests, and what pins bytes (CHT-92..94): the published chart's nine third-party images (Keycloak, Postgres, Elasticsearch, Prometheus, Loki, Tempo, Grafana, the collector, curl) are digest-pinned inside it, so an install pulls exactly those manifests. Aurelius images stay tag-referenced (`:<release>` tags written only by the signed publish chain) — the chart signature names the release, and the chart version itself is immutable in the registry. An operator who wants to freeze one own image to a digest can set its `image.digest` (e.g. `atlas-server.image.digest= sha256:<hex>`); the field exists for that, and a set digest always wins over the tag. Enforcing signatures **at admission** (a cluster policy rejecting unverified images) is deliberately left to the operator: the mechanism is cluster posture, not chart content.

The umbrella generates the credentials (Elasticsearch password, Keycloak admin/DB passwords, the OTel ingest client secrets, legacy token) at first install and preserves them across upgrades; retrieve them with `kubectl get secret`. On the hardened realm, `<release>-otel-clients` carries **one key per ingest client** — `otel-atlas-server`, `otel-data2model`, `otel-elasticsearch`, `otel-keycloak`, `otel-lineage-model`, `otel-postgres`, `otel-validate-entity` (CHT-88, DD-277) — each generated and preserved independently; `master` keeps the single shared `OTEL_INGEST_CLIENT_SECRET` key. To rotate one leaked producer's credential, supply its new value and upgrade (`--set secrets.otelClients.clients.<client-id>=<secret>` or its `clients:` values entry), then re-import the realm or reset that one client's secret in the Keycloak console (the import applies at first boot only) and restart the producer — the other six clients are untouched either way, which is the point of the per-client shape.

> \[!WARNING\] With `--wait` (or `--atomic`), a workload that never reaches Ready — a crash-loop, a Secret the chart expects but nobody created — burns the full `--timeout` and leaves the release stuck at `pending-install`; every later `helm upgrade` then fails with "another operation … is in progress" until `helm uninstall atlas -n atlas` clears it (DD-298). Fix the cause (check `kubectl -n atlas get pods` / `helm history atlas -n atlas`), then uninstall and reinstall — do not wait the release out.

## 2\. Validate

```
kubectl -n atlas get pods                          # all Running/Completed
kubectl -n atlas get gateway,gatewayclass,httproute
curl -k https://<domain>/api/atlas/admin/liveness
curl -k https://auth.<domain>/realms/aurelius-atlas    # issuer reachable
```

### Grafana

Grafana has no anonymous access: the login screen's **Keycloak** button goes to the `aurelius-atlas` realm (CHT-84, DD-275). The roles on the `grafana` client gate the door (CHT-85, CHT-136, DD-659). The `admin` role lands as Grafana **Admin**, and the `editor` role lands as **Editor**. A realm user who holds neither role is denied at the callback, because the mapping has no Viewer fallback any more. You assign the roles on the `grafana` client in the Keycloak console or through the admin API. The daily door is the browser host: `global.hosts.o11y.enabled` is true by default (DD-653), and Grafana builds its login redirect from `GF_SERVER_ROOT_URL`, which the chart pins to `https://observability.<domain>` whenever the host is on (DD-654):

```
https://observability.<domain>   # log in with the Keycloak button
```

The port-forward path still works when you set `global.hosts.o11y.enabled=false`: the pin drops, the UI becomes request-derived again, and the client's registered `http://localhost:3000/login/generic_oauth` completes the login (DD-276). With the host on, a forwarded port redirects to the public host instead. The generated local admin (`<release>-grafana-admin`, keys `user`/`password` via `kubectl get secret`) is the account-recovery credential — use it only when the realm path is broken. Keycloak's 8443 NetworkPolicy admits Grafana for the token exchange (CHT-86); if the login redirects but never completes, check that hop first. The OIDC call needs the private CA in the pod's trust store, which the chart mounts (DD-654); the backend hop to Grafana is plaintext, and the edge's HTTP health check probes `/api/health` (DD-653).

On first boot Grafana downloads its datasource plugins (prometheus, loki, tempo — external in 13) from the public catalog, so the pod needs egress to it; a cluster without one must prefill the Grafana PVC's plugin directory by other means (DD-657). Until that download finishes, panels answer `plugin.notRegistered` — this is expected on a fresh install, not a broken setup.

## 3\. Upgrade

```
helm upgrade atlas oci://ghcr.io/aureliusenterprise/charts/aurelius-atlas \
    --version <chart-version> \
    -f helm/environments/<env>.yaml \
    --namespace atlas
```

### Rename the browser hosts

The browser hosts have moved twice. A release before increment 10.15 named them after the component (`atlas`, `keycloak`, `grafana`); a release before ADR 069 named them `app.<domain>` and `o11y.<domain>`. The current shape puts the product at the zone apex (`<domain>`) and observability at `observability.<domain>` (ADR 069), while the values keys stay `app`, `auth`, `dashboard`, and `o11y` (CHT-135, DD-658). The chart has no alias for an old key or an old host, because a half-renamed install serves two hostnames for one app. Add the target records first, then upgrade, then retire the old names.

> [!WARNING]

**The issuer moves with the rename.** Keycloak advertises `https://auth.<domain>` after it, and every token embeds the `iss` it was minted with. Tokens, sessions, and Grafana logins issued before the upgrade stop validating. Do the rename as one change, in one maintenance window.

1. Add the new public records next to the old ones. Let's Encrypt must see them before the upgrade, because ACME validates all SANs of the new edge leaf. The product sits at the apex, so its record is at `<domain>.` itself (a wildcard would not cover it), and the other hosts are subdomains:

   ```
   gcloud dns record-sets create "<domain>." --zone=<public-zone> \
       --type=A --rrdatas=<gateway-ip> --ttl=300          # the product (apex)
   for host in auth observability; do
       gcloud dns record-sets create "$host.<domain>." --zone=<public-zone> \
           --type=A --rrdatas=<gateway-ip> --ttl=300
   done
   ```
2. Update the private zone (DD-651): `auth.<domain>` must resolve to the Keycloak Service ClusterIP in-cluster, as the sign-in host did before. Keep the old records until the last step.
3. Upgrade the release. A pre-10.15 overlay also renames its `hosts:` keys (a `hosts.grafana.enabled` entry becomes `hosts.o11y.enabled`). The Keycloak pod restarts and re-imports the realm with the new placeholder hosts; restart the collectors and every OIDC client afterwards so they re-read the issuer metadata.
4. Verify the new hosts answer (section 2), then delete the old `atlas`, `keycloak`, and `grafana` records from both zones.

### Admin accounts

The realm asset carries no users (CHT-80), so you create the first humans through the admin API. Three doors read three separate parts of the token: the `admin` role of the `grafana` client opens Grafana (CHT-136), the `realm-admin` role of the `realm-management` client opens the Keycloak console, and the four `atlas-*` client roles of the `aurelius-atlas-server` client open the Atlas API (AUZ-02). An admin grant opens only its own door, so the sequence below gives each account all of them, plus a temporary password with a forced change at first login, plus membership in the `aurelius` organization's read group. Server tenancy is off by default, so the organization membership stages the data and changes no access yet. Switching it on ([ADR 063](<https://aureliusenterprise.github.io/feat-12-9-demo-quality-scores/architecture/adr/063-each-tenant-is-an-organization-with-its-own-store/index.md>)) makes every read and write consult what these groups and roles already hold.

```
KC=https://localhost:8444   # after: kubectl port-forward svc/atlas-keycloak 8444:8443
TOKEN=$(curl -sk -X POST "$KC/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    -d username="$(kubectl -n atlas get secret atlas-keycloak-admin -o jsonpath='{.data.user}' | base64 -d)" \
    -d password="$(kubectl -n atlas get secret atlas-keycloak-admin -o jsonpath='{.data.password}' | base64 -d)" \
    | uv run python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

> [!WARNING]

**`clientRoles` keys are client *names*, and a wrong key fails silently.** Keycloak applies the map only for keys that name a client of the realm; an id-keyed or misspelled map creates the user with no roles and answers 201. Make sure that a later `GET /users/<id>/role-mappings/clients/<client-id>` lists each role before you hand over the account. (The same endpoint answers a bare `[]`, not a `clientMappings` object, while the user holds no roles.)

For each account, create the user with the roles and required action (save the password to a file you delete after the handover, never to a log):

```
USER=<username>                 # e.g. jane.doe
PASS=$(openssl rand -base64 15)
curl -sk -X POST "$KC/admin/realms/aurelius-atlas/users" -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' -d "{
  \"username\": \"$USER\", \"enabled\": true,
  \"email\": \"$USER@<your-domain>\", \"emailVerified\": true,
  \"requiredActions\": [\"UPDATE_PASSWORD\"],
    \"credentials\": [{\"type\": \"password\", \"value\": \"$PASS\", \"temporary\": true}],
  \"clientRoles\": {\"grafana\": [\"admin\"],
    \"aurelius-atlas-server\": [\"atlas-read\", \"atlas-write\", \"atlas-types\", \"atlas-admin\"]}
}"
echo "$USER $PASS" >>/tmp/admin-accounts.txt
```

The console door needs one more call, because `realm-admin` is a client role of the internal `realm-management` client: fetch that client's id and `POST` the role object to `/users/<id>/role-mappings/clients/<rm-id>`. A user of that role signs in once with the temporary password, sets a real one, and reaches Grafana as Admin, the Keycloak console as administrator, and the Atlas API with its full four-role set. The `atlas-*` roles are client roles of `aurelius-atlas-server` today, and the organization's four groups carry the same names for the tenancy-on posture (TEN-02), so a tenancy switch re-reads what each account already holds. A realm user that holds no `grafana` client role shows the denial case: the strict mapping refuses it at the callback (CHT-136).

Finish with the organization, once per realm. The calls mirror what the server's provisioning module does when tenancy is on (`realm_tenants.py`, ADR 063), so enabling tenancy finds the tenant already staged:

```
ORG_ID=$(curl -sk -X POST "$KC/admin/realms/aurelius-atlas/organizations" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d '{"name": "aurelius", "alias": "aurelius", "enabled": true}' \
    | cut -d/ -f9)
for GROUP in atlas-read atlas-write atlas-types atlas-admin; do
    curl -sk -X POST "$KC/admin/realms/aurelius-atlas/organizations/$ORG_ID/groups" \
        -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
        -d "{\"name\": \"$GROUP\"}"
done
READ_ID=$(curl -sk "$KC/admin/realms/aurelius-atlas/organizations/$ORG_ID/groups" \
    | uv run python -c 'import json,sys; print([g["id"] for g in json.load(sys.stdin) if g["name"]=="atlas-read"][0])')
for USER in jane.doe john.smith; do
    UID_=$(curl -sk "$KC/admin/realms/aurelius-atlas/users?username=$USER&exact=true" \
        -H "Authorization: Bearer $TOKEN" \
        | uv run python -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
    curl -sk -X POST "$KC/admin/realms/aurelius-atlas/organizations/$ORG_ID/members" \
        -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "\"$UID_\""
    curl -sk -X PUT "$KC/admin/realms/aurelius-atlas/organizations/$ORG_ID/groups/$READ_ID/members/$UID_" \
        -H "Authorization: Bearer $TOKEN"
done
```

The member POST takes the bare user id as `text/plain` (the shape `realm_tenants.py` uses). With tenancy off, the membership changes no access yet; with it on, the `organization` claim and the `organization.aurelius.groups` list decide what each user reads and writes.

## 4\. Uninstall

```
helm uninstall atlas -n atlas
```

The Elasticsearch and Keycloak data volumes survive (the PVCs are not owned by the release); delete them deliberately — see the backup duties in ADR 026.

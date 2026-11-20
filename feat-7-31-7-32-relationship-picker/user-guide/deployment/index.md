# Deploy to Kubernetes

Aurelius Atlas runs on Kubernetes and ships as Helm charts. This page takes you from an empty cluster to a running system that people sign in to: the prerequisites, the install, how to tell that it worked, and the first administrators. It covers the two shapes the project tests, a local minikube cluster and a GKE cluster.

This page is the guided path. The [deployment reference](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/index.md>) explains why the system has this shape, and the [runbook](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/runbook/index.md>) carries every DNS, certificate, and rename edge in full. This page links them instead of repeating them.

To run the server on one machine without a cluster, see [Standalone Server](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/user-guide/standalone-server/index.md>) instead.

## What you install

You install one Helm release into one namespace (default: `atlas`). The `aurelius-atlas` umbrella composes eight component charts: the Atlas API, the dashboard, three auxiliary APIs, the Elasticsearch store, the Keycloak issuer, and the observability stack. The umbrella also owns the shared edge, the trust issuers, and the generated Secrets. The [deployment reference](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/#topology>) holds the topology and the component table.

```
flowchart LR
    prep[Prepare the cluster] -->|helm install| live[System running]
    live -->|create administrators| users[People sign in]
    live -->|helm upgrade| live
```

Each cluster needs the prerequisites once, and every later change is an upgrade of the same release ([ADR 057](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>)).

> [!NOTE]
>
> **The scanner charts are separate**
>
> The three batch scanner charts install as their own releases and never travel with the umbrella. See [Scanner charts install on their own](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/#scanner-charts-install-on-their-own>).

## Before you start

A cluster must carry a few things before the first install. The [runbook prerequisites](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/runbook/#0-prerequisites>) give the exact command for each one.

- `kubectl` bound to your cluster context, and Helm.
- cert-manager (CRDs and controller). The whole trust model depends on it.
- A GatewayClass named in `global.gateway.className`.
- trust-manager, whose trust namespace is your install namespace. Without it, the install fails on a missing `Bundle` resource.
- Pull Secrets for the private registries (`dhi.io` and `ghcr.io`) when the cluster cannot pull them anonymously.
- Public DNS records for each browser host when a public Let's Encrypt edge signs them.

> [!WARNING]
>
> **Pick the domain now, because you cannot change it later**
>
> The Keycloak issuer URL derives from `global.domain`, and every token embeds that URL. After the system stores data, a domain change invalidates every token and every saved reference. Choose the final hostname before the first install. The same rule holds for `global.realm`.

> [!WARNING]
>
> **In-cluster producers need the issuer's public name**
>
> With observability on, in-cluster jobs reach Keycloak by its public host (`auth.<domain>`), so that name must resolve to the Keycloak Service inside the cluster too. The runbook's [split-horizon DNS step](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/runbook/#0-prerequisites>) covers both minikube (a CoreDNS rewrite) and GKE (a private Cloud DNS zone). On GKE with a public edge, this is a hard prerequisite, not an optimization.

## Choose an environment

An environment is a values overlay, not a separate chart. The repository ships two tested overlays. Copy one, then set `global.domain` to your real domain.

| Overlay | Gateway class | Edge trust | Hosts | For |
| --- | --- | --- | --- | --- |
| `minikube.yaml` | `envoy-gateway` | chart self-signed | `*.atlas.test` | local/dev, in devcontainer |
| `gke.yaml` | `gke-l7-global-external-managed` | Let's Encrypt + private CA | your domain | GKE (the documented target) |

On minikube, start `minikube tunnel` in a second terminal and point your hosts file (`app.atlas.test`, `auth.atlas.test`, and `o11y.atlas.test` if enabled) at `127.0.0.1`. On GKE, enable the managed Gateway TLS APIs first: the Certificate Manager API is required or the edge refuses TLS and health checks. The `gke.yaml` overlay already sets the health check and the ECDSA edge key that GKE needs.

## Install

Install the published umbrella with your overlay. The published chart carries its component charts, so no extra step is needed.

```
helm install atlas oci://ghcr.io/aureliusenterprise/charts/aurelius-atlas \
    --version <chart-version> \
    -f <your-overlay>.yaml \
    --namespace atlas
```

To install from a repository checkout instead, resolve the component charts first with `helm dep update helm`, then run `helm install atlas helm` with the same flags.

Before you install a version, make sure that the chart carries the project's publish signature (the same identity its images carry):

```
cosign verify ghcr.io/aureliusenterprise/charts/aurelius-atlas:<chart-version> \
    --certificate-identity-regexp '^https://github\.com/aureliusenterprise/aurelius-atlas/\.github/workflows/publish\.yaml@' \
    --certificate-oidc-issuer-regexp '^https://token\.actions\.githubusercontent\.com$'
```

The umbrella generates each credential (the Elasticsearch password, the Keycloak admin and database passwords, the ingest client Secrets) at the first install, then keeps it on every upgrade. Read one with `kubectl get secret`. The [secret storage](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/secret-storage/index.md>) page explains the generate-and-preserve rule.

## Make sure that the install worked

The pods come up, then the edge and the issuer answer.

```
kubectl -n atlas get pods                          # all Running or Completed
kubectl -n atlas get gateway,gatewayclass,httproute
curl -k https://app.<domain>/api/atlas/admin/liveness
curl -k https://auth.<domain>/realms/aurelius-atlas    # issuer reachable
```

> [!TIP]
>
> **Grafana panels stay blank for the first minute**
>
> On its first boot, Grafana downloads its Prometheus, Loki, and Tempo plugins, so panels answer `plugin.notRegistered` until that download ends. This is expected, not a broken setup.

## Create the first administrators

The shipped realm carries no users, so you create the first people through the Keycloak admin API. Each admin surface reads a different part of the token, so give a first account the roles for every door you want it to open.

| Door | Opens with the role of |
| --- | --- |
| The Atlas API | `aurelius-atlas-server` (`atlas-read`/`-write`/`-types`/`-admin`) |
| The Keycloak console | `realm-management` (`realm-admin`) |
| Grafana | `grafana` (`admin` or `editor`) |

Read the bootstrap admin credential, mint a token, then create the user with the roles and a password it must change on first login.

```
KC=https://localhost:8444   # after: kubectl port-forward svc/atlas-keycloak 8444:8443
TOKEN=$(curl -sk -X POST "$KC/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    -d username="$(kubectl -n atlas get secret atlas-keycloak-admin -o jsonpath='{.data.user}' | base64 -d)" \
    -d password="$(kubectl -n atlas get secret atlas-keycloak-admin -o jsonpath='{.data.password}' | base64 -d)" \
    | tr ',' '\n' | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
USER=<username>
curl -sk -X POST "$KC/admin/realms/aurelius-atlas/users" -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' -d "{
  \"username\": \"$USER\", \"enabled\": true,
  \"requiredActions\": [\"UPDATE_PASSWORD\"],
  \"clientRoles\": {\"grafana\": [\"admin\"],
    \"aurelius-atlas-server\": [\"atlas-read\", \"atlas-write\", \"atlas-types\", \"atlas-admin\"]}
}"
```

> [!WARNING]
>
> **A wrong role key fails with a 201**
>
> The `clientRoles` map is keyed by the client's name, not its id. A misspelled or id-keyed entry creates the user with no roles and still answers `201`. Read the user's role mappings back before you hand over the account. The [runbook admin step](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/runbook/#admin-accounts>) adds email and password-policy detail and a generated password.

A script that calls the Atlas API uses a service client and a client-credentials token, not a person's password. The scanners and the provisioning command already work this way, and the server accepts their tokens by default.

## Sign in

Open the dashboard at `https://app.<domain>` and sign in with the Keycloak button. Open the observability stack at `https://o11y.<domain>`. Its Grafana login also runs through Keycloak, and only the `admin` or `editor` role of the `grafana` client passes the door. The generated `atlas-grafana-admin` Secret is an account-recovery credential, for use only when the realm path is broken. The [runbook Grafana section](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/runbook/#grafana>) covers the full login path in detail.

## Turn on tenancy (optional)

Tenancy is off by default, and the server then answers as Apache Atlas does. Set `tenancy.enabled` and list your tenants in `tenancy.tenants` to switch it on ([ADR 063](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/adr/063-each-tenant-is-an-organization-with-its-own-store/index.md>)). Each tenant is a Keycloak organization with its own store. A provisioning hook runs after every install and upgrade and leaves an existing tenant alone, so you remove a tenant with the server's command, never by dropping it from the list. To add a tenant on the standalone server, see [Add a Tenant](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/user-guide/standalone-tenants/index.md>).

## Upgrade

Run the same install command as an upgrade. The umbrella keeps every live credential, so an upgrade never rotates a password.

```
helm upgrade atlas oci://ghcr.io/aureliusenterprise/charts/aurelius-atlas \
    --version <chart-version> \
    -f <your-overlay>.yaml \
    --namespace atlas
```

## If the install gets stuck

> [!WARNING]
>
> **A `--wait` install can hang the release**
>
> With `--wait` or `--atomic`, a workload that never reaches `Ready` burns the whole timeout and leaves the release at `pending-install`. Every later upgrade then fails with "another operation is in progress" until you clear it. Read `kubectl -n atlas get pods` and `helm history atlas -n atlas`, fix the cause, then `helm uninstall atlas -n atlas` and reinstall.

To remove the system:

```
helm uninstall atlas -n atlas
```

Because the issuer is first-boot-immutable, a fresh install on the same domain re-creates the realm and the credentials from scratch, so it is not a way to recover the previous data.

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| Pods stay `ImagePullBackOff` | The cluster cannot pull from `dhi.io` or `ghcr.io`. Create the pull Secrets named in [Before you start](<#before-you-start>). |
| Install fails with a missing `Bundle` | trust-manager is absent, or its trust namespace is not the install namespace. See [Before you start](<#before-you-start>). |
| A browser host's certificate stays `Pending` | DNS-01 cannot see the challenge in public DNS. See the [ACME edge step](<https://aureliusenterprise.github.io/feat-7-31-7-32-relationship-picker/architecture/deployment/runbook/#0-prerequisites>). |
| Panels answer `plugin.notRegistered` | The first-boot plugin download is still running. Wait a minute, then reload the page. |

Each fix above points at the step that owns the detail.

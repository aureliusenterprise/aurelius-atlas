# GKE self-hosted CI runners (Phase 1)

ARC (`gha-runner-scale-set`) runner pods for `aureliusenterprise/aurelius-atlas`,
so the `ci` job runs in the dev container on GKE (plan:
[`docs/architecture/self-hosted-ci.md`](../../docs/architecture/self-hosted-ci.md)).

Layout of one job: runner pod (ARC stock runner image) + **dind sidecar**
(privileged `docker:dind`, unix socket at `/var/run/docker.sock` shared with
the runner container). `devcontainers/ci` starts the dev container as a sibling
on that sidecar - exactly the hosted-runner topology, so nothing in
`.github/actions/run-in-devcontainer` changes.

## One-time setup

Prereqs: the **atlas-dev Standard cluster** (europe-west1 - verified: no
Autopilot constraints, privileged pods admitted), a GitHub App installed on
the repo with **Actions: read/write** (not a PAT - App credentials rotate
cleanly). The `gcloud`/`kubectl`/`helm` CLIs come from the dev container
(`./features/google-cloud-cli` - vendored dhoeric, with
`installGkeGcloudAuthPlugin`; `kubectl-helm-minikube` - gated by
`.devcontainer/smoke.sh`), so run these from inside it, after
`gcloud auth login --no-launch-browser` +
`gcloud config set project aurelius-atlas` +
`gcloud container clusters get-credentials atlas-dev --location europe-west1`.

Phase 1 runs the **canary on the existing default pool** (nodes: 3.92 CPU /
13.9 Gi allocatable, low requests) with canary-sized requests - no new node
pool, no cache PVC, no marginal cost. The dedicated tainted spot pool and
the PVC are Phase 2 (the full pipeline needs ~6 vCPU / ~30 GB, which a
13.9 Gi node cannot hold); the taint/selector and cache volume are
commented in `arc-values.yaml` for that step.

```bash
# 1. Controller (cluster-scoped, one per cluster) - DONE 2026-10-25:
helm install arc oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
    --namespace arc-systems --create-namespace

# 2. App auth secret (values in GITHUB_APP_ID / GITHUB_APP_INSTALLATION_ID /
#    GITHUB_APP_PRIVATE_KEY_FILE) - needs the GitHub App first, see below:
kubectl create namespace arc-runners
kubectl -n arc-runners create secret generic atlas-arc-auth \
    --from-literal=github_app_id="$GITHUB_APP_ID" \
    --from-literal=github_app_installation_id="$GITHUB_APP_INSTALLATION_ID" \
    --from-file=github_app_private_key="$GITHUB_APP_PRIVATE_KEY_FILE"

# 3. The scale set (namespaced, per repo):
helm install atlas-ci oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
    --namespace arc-runners -f infra/arc/arc-values.yaml

# Phase 2 only - dedicated CI pool + cache volume:
GCP_PROJECT=aurelius-atlas GKE_CLUSTER=atlas-dev GKE_LOCATION=europe-west1 ./install.sh nodepool
kubectl apply -f infra/arc/toolchain-cache-pvc.yaml
```

**GitHub App** (org owner, one time): open
github.com/organizations/aureliusenterprise/settings/apps/new → name it
`atlas-arc`, Homepage `https://github.com/aureliusenterprise/aurelius-atlas`,
Webhook: uncheck "Active" (ARC needs no webhook), Repo permissions:
**Actions: Read and write**, Metadata: Read-only (that is all ARC needs).
Generate a private key, save it outside git (e.g. `~/atlas-arc.pem`, chmod 600).
Install the App on `aureliusenterprise/aurelius-atlas` only (Install →
"Only select repositories"). The installation id is in the install URL
(`/settings/installations/<id>`); the app id is on the App's General page.
`GITHUB_APP_ID` / `GITHUB_APP_INSTALLATION_ID` /
`GITHUB_APP_PRIVATE_KEY_FILE` then feed the secret above. The runner labels
(`scaleSetLabels: atlas-ci`) are what `runs-on:` selects via `CI_RUNS_ON`.

Cost/benefit + the option analysis:
[`docs/architecture/self-hosted-ci-decision.md`](../../docs/architecture/self-hosted-ci-decision.md).

## Flag day (repo side)

Once a canary job scheduled on the pool is green, flip the repo variables -
the workflow reads them, unset means hosted:

```bash
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_RUNS_ON \
    -f name=CI_RUNS_ON -f value=atlas-ci
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_DISK_CLEANUP \
    -f name=CI_DISK_CLEANUP -f value=false
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_USE_ACTIONS_CACHE \
    -f name=CI_USE_ACTIONS_CACHE -f value=false   # unavailable on self-hosted (private repos)
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_CACHE_MOUNTS \
    -f name=CI_CACHE_MOUNTS -f value='atlas-toolchain-cache:/workspaces/aurelius-atlas/.container-cache'
```

Deleting the variables reverts to hosted runners - no PR needed.

Notes:

- GHCR pulls of `atlas-ci-runner:main` carry credentials from the composite's
  login step (the docker client sends them to the sidecar) - no
  `imagePullSecrets` needed; the pod's own images are public.
- `cache-mounts` binds the PVC into the dev container; on hosted the same
  paths are filled by `actions/cache` instead (`use-actions-cache`).
- The `.features-cache` dir under `.devcontainer/` is inside the checkout
  (gitignored) and lands on the job's `work` volume - features rebuild
  ~weekly (hash-keyed), acceptable for now; a second volume mount is the
  escape hatch if it hurts.
- **Rollback**: `helm uninstall atlas-ci -n arc-runners` + delete variables.

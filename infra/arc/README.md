# AKS self-hosted CI runners (Phase 1)

ARC (`gha-runner-scale-set`) runner pods for `aureliusenterprise/aurelius-atlas`,
so the `ci` job runs in the dev container on AKS (plan:
[`docs/architecture/self-hosted-ci.md`](../../docs/architecture/self-hosted-ci.md)).

Layout of one job: runner pod (ARC stock runner image) + **dind sidecar**
(privileged `docker:dind`, unix socket at `/var/run/docker.sock` shared with
the runner container). `devcontainers/ci` starts the dev container as a sibling
on that sidecar - exactly the hosted-runner topology, so nothing in
`.github/actions/run-in-devcontainer` changes.

## One-time setup

Prereqs: an AKS cluster (>= 1.29), a GitHub App installed on the repo with
**Actions: read/write** (not a PAT - App credentials rotate cleanly). The
`az`/`kubectl`/`helm`/`kubelogin` CLIs come from the dev container
(`ghcr.io/devcontainers/features/azure-cli`, `kubectl-helm-minikube`,
`./features/kubelogin` - gated by `.devcontainer/smoke.sh`), so run these
from inside it.

```bash
# 1. Controller (cluster-scoped, one per cluster):
helm install arc oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
    --namespace arc-systems --create-namespace

# 2. App auth secret (values in GITHUB_APP_ID / GITHUB_APP_INSTALLATION_ID /
#    GITHUB_APP_PRIVATE_KEY_FILE):
kubectl create namespace arc-runners
kubectl -n arc-runners create secret generic atlas-arc-auth \
    --from-literal=github_app_id="$GITHUB_APP_ID" \
    --from-literal=github_app_installation_id="$GITHUB_APP_INSTALLATION_ID" \
    --from-file=github_app_private_key="$GITHUB_APP_PRIVATE_KEY_FILE"

# 3. Toolchain cache volume (Azure Files, shared ReadWriteMany):
kubectl apply -f infra/arc/toolchain-cache-pvc.yaml

# 4. The scale set (namespaced, per repo):
helm install atlas-ci oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
    --namespace arc-runners -f infra/arc/arc-values.yaml
```

The CI node pool is created by `./install.sh nodepool` (needs `--resource-group`
/ `--cluster-name` via env) - spot D8s v5, scale 0..3, tainted so only CI pods
land there.

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

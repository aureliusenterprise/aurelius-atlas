# GKE self-hosted CI runners (Phases 1-2)

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
Autopilot constraints, privileged pods admitted) and a **classic PAT with
the `repo` scope** in the auth secret (see "Auth" below - the GitHub App
we also created is blocked by plan gating on this repo today). The
`gcloud`/`kubectl`/`helm` CLIs come from the dev container
(`./features/google-cloud-cli` - vendored dhoeric, with
`installGkeGcloudAuthPlugin`; `kubectl-helm-minikube` - gated by
`.devcontainer/smoke.sh`), so run these from inside it, after
`gcloud auth login --no-launch-browser` +
`gcloud config set project aurelius-atlas` +
`gcloud container clusters get-credentials atlas-dev --location europe-west1`.

Phase 1 ran the **canary on the existing default pool** (nodes: 3.92 CPU /
13.9 Gi allocatable) - gate passed 5/5, zero marginal cost. Phase 2 (live
2026-10-25) added the **toolchain-cache PVC** and flipped the repo
variables; the full pipeline runs on the same default pool (no new node
pool - if it ever exceeds capacity, constrain the dev docker composes
first, see the decision doc). The dedicated tainted spot pool stays
documented-but-unused: uncomment the taint/selector block in
`arc-values.yaml` to enable it.

```bash
# 1. Controller (cluster-scoped, one per cluster) - DONE 2026-10-25:
helm install arc oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
    --namespace arc-systems --create-namespace

# 2. Auth secret (classic PAT, `repo` scope, in GITHUB_PAT - see Auth):
kubectl create namespace arc-runners
kubectl -n arc-runners create secret generic atlas-arc-auth \
    --from-literal=github_token="$GITHUB_PAT"

# 3. The scale set (namespaced, per repo):
helm install atlas-ci oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
    --namespace arc-runners -f infra/arc/arc-values.yaml

# Phase 2 (live) - cache volume:
kubectl apply -f infra/arc/toolchain-cache-pvc.yaml
# then `./install.sh scale-set` (work volume + cache-init in arc-values.yaml)
```

**Auth (measured 2026-10-25 on this org).** `POST
/actions/runners/registration-token` - the call ARC reconciles with:

| Credential                         | Result                                                             |
| ---------------------------------- | ------------------------------------------------------------------ |
| Classic PAT (`repo`) / OAuth token | 201                                                                |
| Fine-grained PAT (Actions: write)  | 403 (runner-management endpoints accept classic scopes only)       |
| GitHub App (Actions: write)        | 403 (App runner endpoints need Enterprise Cloud; this org is Team) |

So the secret carries a **classic PAT** (github.com/settings/tokens/new,
`repo` scope, 90-day expiry, store outside git). Rotation:

```bash
kubectl -n arc-runners create secret generic atlas-arc-auth \
    --from-literal=github_token="$GITHUB_PAT" \
    --dry-run=client -o yaml | kubectl apply -f -
```

then `./install.sh scale-set`.

The **atlas-arc GitHub App** (app 5466493, install 175110388, key kept
off-git) is installed and ready for the Enterprise flip: recreate the
secret with the three `github_app_*` keys (the chart auto-detects). Note
the org also required **Runner groups → Default → "Allow public
repositories"** - this repo is public, and GitHub refuses self-hosted
registration for public repos in groups that disallow them. The
`scaleSetLabels: atlas-ci` label is what `runs-on:` selects via
`CI_RUNS_ON`.

Cost/benefit + the option analysis:
[`docs/architecture/self-hosted-ci-decision.md`](../../docs/architecture/self-hosted-ci-decision.md).

## Flag day (repo side) - DONE 2026-10-25

The five repo variables, set as live (unset any to revert that knob to
hosted):

```bash
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_RUNS_ON \
    -f name=CI_RUNS_ON -f value=atlas-ci
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_DISK_CLEANUP \
    -f name=CI_DISK_CLEANUP -f value=false
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_USE_ACTIONS_CACHE \
    -f name=CI_USE_ACTIONS_CACHE -f value=false   # unavailable on self-hosted (private repos)
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_CACHE_MOUNTS \
    --input - <<'EOF'   # newline-separated devcontainers/ci mounts; targets OUTSIDE the checkout
{"value":"type=bind,source=/home/runner/_work/.ci-cache/uv,target=/var/cache/ci/uv\ntype=bind,source=/home/runner/_work/.ci-cache/npm,target=/var/cache/ci/npm\ntype=bind,source=/home/runner/_work/.ci-cache/pre-commit,target=/var/cache/ci/pre-commit"}
EOF
gh api -X PUT repos/aureliusenterprise/aurelius-atlas/actions/variables/CI_CACHE_ENV \
    --input - <<'EOF'   # container-side cache dirs = the mount targets above
{"value":"UV_CACHE_DIR=/var/cache/ci/uv\nnpm_config_cache=/var/cache/ci/npm\nPRE_COMMIT_HOME=/var/cache/ci/pre-commit"}
EOF
```

Deleting the variables reverts to hosted runners - no PR needed.

Notes:

- GHCR pulls of `atlas-ci-runner:main` carry credentials from the composite's
  login step (the docker client sends them to the sidecar) - no
  `imagePullSecrets` needed; the pod's own images are public.
- **Caches live outside the checkout.** `CI_CACHE_MOUNTS` binds the PVC's
  `.ci-cache/*` dirs (pre-created setgid 2775 by the `cache-init` init
  container) to `/var/cache/ci/*` in the dev container, and `CI_CACHE_ENV`
  points `UV_CACHE_DIR`/`npm_config_cache`/`PRE_COMMIT_HOME` at the same
  paths. Mounting them _inside_ the checkout (`.container-cache/*`, as
  first planned) breaks the next job: dockerd creates bind-mount targets as
  root:root and `actions/checkout`'s `git clean -ffdx` then fails with
  EACCES (run 40201875108). `cache-init` also sweeps any such stale dirs.
  The mounts must match `CI_CACHE_ENV` exactly - a mismatch means the tools
  see an unwritable empty dir (`/var/cache/ci` parent dirs are created
  root-owned by dockerd, the setgid source dirs make writes work).
- On hosted, the same cache dirs are filled by `actions/cache` instead
  (`use-actions-cache`), at the action's default in-workspace paths.
- The `.features-cache` dir under `.devcontainer/` is inside the checkout
  (gitignored) and lands on the job's `work` volume - features rebuild
  ~weekly (hash-keyed), acceptable for now; a second volume mount is the
  escape hatch if it hurts.
- **Rollback**: `helm uninstall atlas-ci -n arc-runners` + delete variables.

## Shape A - jobs run IN the dev container image (canary)

The goal state from the decision doc: the runner pod's job container **is**
`ghcr.io/aureliusenterprise/atlas-ci-runner` (the dev container), so CI steps
run directly in the developer image - no `devcontainers/ci`, no sibling
container, no per-job 8.3 GB image pull. The `atlas-ci` scale set above is
**Shape B** (stock runner + devcontainers/ci) and keeps serving the full `ci`
job while this canary proves Shape A.

Pieces (each verified against chart 0.15.1 / the baked feature scripts):

- `ci-runner` devcontainer feature (`.devcontainer/features/ci-runner`) bakes
  the Actions runner binaries at `/opt/actions-runner` (vscode-owned). Harmless
  in developer containers - nothing launches them there.
- The `docker-in-docker` feature (already present) bakes `dockerd` +
  `/usr/local/share/docker-init.sh`, which starts the daemon then
  `exec "$@"` - the pod command chains it to `run.sh`. The pod is
  **privileged** (the feature's own manifest says the same for dev containers).
- `arc-shapea-values.yaml`: default containerMode (the chart passes the
  container through verbatim - registration env comes from the controller),
  `runAsUser: 1000` (vscode) + docker group 999 (k8s drops the image user's
  supplementary groups; dockerd's socket is `root:docker` 0660), `work` +
  `dind-storage` emptyDirs, label `atlas-ci-shapea`, `maxRunners: 1`.
- `.github/workflows/ci-shapea.yaml`: direct steps (toolchain sanity with a
  real `docker info`, the devcontainer lifecycle scripts, pre-commit).

Deploy loop (from the dev container, kube context on atlas-dev):

```bash
# One-time: GHCR pull secret for the private package (PAT needs
# write:packages too - the image is private). Recreate on PAT rotation:
TOK=$(tr -d '\n' < ~/atlas-arc-pat.txt)
AUTH=$(printf '%s:%s' "$(gh api user -q .login)" "$TOK" | base64 -w0)
kubectl -n arc-runners create secret generic atlas-ghcr-pull \
    --type=kubernetes.io/dockerconfigjson \
    --from-literal=".dockerconfigjson={\"auths\":{\"ghcr.io\":{\"auth\":\"$AUTH\"}}}"

# Image: push a commit that touches .devcontainer/** -> the build workflow
# publishes atlas-ci-runner:sha-<full-sha> (branch builds publish their own
# tag; main publishes :main). Then:
CI_SHAPEA_IMAGE_TAG=sha-<full-sha> ./install.sh scale-set-shapea
gh workflow run ci-shapea.yaml --ref feat/validate-job-in-devcontainer
```

Canary gate: green on the pool, repeated; then the cache bridge (PVC mounts
for `/var/cache/ci/*` + the docker image store, mirroring `CI_CACHE_MOUNTS`)
is the next increment before the full `ci` job flips. Rollback:
`helm uninstall atlas-ci-shapea -n arc-runners` (Shape B is untouched).

Measured (first green, run 40214518758, node-warm image): job **3m35s**
(queue 9s) vs 9m10s-9m42s for the same validate-only gate on Shape B - the
setup tax (image pull, devcontainer build, sibling container) disappears.
First pull on a fresh node: 2m17s (2.84 GB compressed), paid once per node.

**Gate passed 5/5** (2026-10-25, runs 40214518758 + 40214880318 + three
dispatches, all 3m35s-class, zero flakes). The scale set then gained the
**cache bridge**: `shapea-cache-pvc.yaml` (dedicated 50 Gi PD - NOT shared
with Shape B: two scale sets on one RWO disk = detach stalls + fsGroup
chown flip-flop) backs the work dir (warm checkout), `/var/cache/ci/*`
(uv/npm/pre-commit, setgid by cache-init), and dockerd's `/var/lib/docker`
(compose/e2e base images survive pods).

# GKE self-hosted CI runners

ARC (`gha-runner-scale-set`) runner pods for `aureliusenterprise/aurelius-atlas`:
the `ci` job runs **directly in the dev container image** on GKE (plan:
[`docs/architecture/self-hosted-ci.md`](../../docs/architecture/self-hosted-ci.md),
decision: [`self-hosted-ci-decision.md`](../../docs/architecture/self-hosted-ci-decision.md)).

Layout of one job: one pod whose job container **is**
`ghcr.io/aureliusenterprise/atlas-ci-runner` (the dev container, built by
`.github/workflows/build-devcontainer-image.yaml`). The container command
chains the docker-in-docker feature's `docker-init.sh` (starts an in-image
privileged `dockerd`, then `exec "$@"`) to `/opt/actions-runner/run.sh`. No
devcontainers/ci wrapper, no dind sidecar, no per-job image pull - the setup
tax of the old hosted/Shape-B topology (8.3 GB pull + devcontainer build +
sibling container, ~5 min) is structurally gone.

The scale set retired 2026-10-25: the former **Shape B** bridge (stock
`actions-runner` + dind sidecar + devcontainers/ci, `atlas-ci` release,
`arc-values.yaml`, `toolchain-cache-pvc.yaml`, the `CI_*` flag-day variables,
`.github/actions/run-in-devcontainer`) is fully removed - git history has it.

## One-time setup

Prereqs: the **atlas-dev Standard cluster** (europe-west1 - verified: no
Autopilot constraints, privileged pods admitted) and a **classic PAT with
the `repo` scope** in the auth secret (see "Auth" - the GitHub App we also
created is blocked by plan gating on this repo today). The
`gcloud`/`kubectl`/`helm` CLIs come from the dev container
(`./features/google-cloud-cli` - vendored dhoeric, with
`installGkeGcloudAuthPlugin`; `kubectl-helm-minikube` - gated by
`.devcontainer/smoke.sh`), so run these from inside it, after
`gcloud auth login --no-launch-browser` +
`gcloud config set project aurelius-atlas` +
`gcloud container clusters get-credentials atlas-dev --location europe-west1`.

```bash
# 1. Controller (cluster-scoped, one per cluster) - DONE 2026-10-25:
helm install arc oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
    --namespace arc-systems --create-namespace

# 2. Auth secret (classic PAT, `repo` scope, in GITHUB_PAT - see Auth):
kubectl create namespace arc-runners
kubectl -n arc-runners create secret generic atlas-arc-auth \
    --from-literal=github_token="$GITHUB_PAT"

# 3. GHCR pull secret for the private runner image (PAT needs
#    write:packages too). Pass the RAW JSON - kubectl base64s it itself:
TOK=$(tr -d '\n' < ~/atlas-arc-pat.txt)
AUTH=$(printf '%s:%s' "$(gh api user -q .login)" "$TOK" | base64 -w0)
kubectl -n arc-runners create secret generic atlas-ghcr-pull \
    --type=kubernetes.io/dockerconfigjson \
    --from-literal=".dockerconfigjson={\"auths\":{\"ghcr.io\":{\"auth\":\"$AUTH\"}}}"

# 4. The cache/work volume + the scale set:
kubectl apply -f infra/arc/shapea-cache-pvc.yaml
CI_SHAPEA_IMAGE_TAG=main ./install.sh scale-set-shapea

# 5. The actions/cache backend for the runners (its own release, safe any
#    time - see "Cache server"):
./install.sh cache-server
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

then `./install.sh scale-set-shapea`.

The **atlas-arc GitHub App** (app 5466493, install 175110388, key kept
off-git) is installed and ready for the Enterprise flip: recreate the
secret with the three `github_app_*` keys (the chart auto-detects). Note
the org also required **Runner groups → Default → "Allow public
repositories"** - this repo is public, and GitHub refuses self-hosted
registration for public repos in groups that disallow them. The
`scaleSetLabels: atlas-ci-shapea` label is what `runs-on:` selects.

Cost/benefit + the option analysis:
[`docs/architecture/self-hosted-ci-decision.md`](../../docs/architecture/self-hosted-ci-decision.md).

## The deploy loop

```bash
# Image: push a commit that touches .devcontainer/** -> the build workflow
# publishes atlas-ci-runner:sha-<full-sha> (main publishes :main). Then:
CI_SHAPEA_IMAGE_TAG=sha-<full-sha> ./install.sh scale-set-shapea
```

`helm upgrade --install` replaces the scale set; in-flight jobs are evicted
(the controller drains), queued jobs requeue onto the new pods. Workflow-only
commits don't need a redeploy - the image tag is a helm `--set`, and the
scale set is only recreated when pod templates change.

## What lives where (the k8s contract, measured 2026-10-25)

Every line here was a failed trial run first. The chart's **default**
container mode (containerMode omitted) passes `template.spec` verbatim and
injects NOTHING into the container - registration arrives via the per-pod
secret (`ACTIONS_RUNNER_INPUT_JITCONFIG`, a secretKeyRef **env var** holding
the JIT token string; the listener consumes it at run.sh boot). Consequences:

- **Work folder**: JIT self-registration writes `WorkFolder: "_work"`
  RELATIVE to the runner root, and there is NO relocating flag - runner
  2.338 `config.sh` has no `--jitconfig` at all (an attempted
  `config.sh --jitconfig` crash-looped the pods), and `RUNNER_WORKSPACE` is
  an ARC kubernetes-mode hook input the standalone listener ignores. The fix
  is what ARC's own hooks do: **mount the work volume AT
  `/opt/actions-runner/_work`** - the default then lands on the PVC. (Jobs
  on the container layer died with `Access to the path
'/opt/actions-runner/_work/_tool' is denied` once `_work` was root-owned.)
- **`SOPS_AGE_KEY_FILE`** = `/var/cache/ci/sops/keys.txt` (a PVC subPath
  cache-init touches every boot). The checkout is EPHEMERAL (see
  "Caches"), so the file cannot live in the tree's `secrets/`; its
  content is irrelevant when `SOPS_AGE_KEY` is in the environment -
  sops needs the FILE to exist.
- **Privileged pod** (in-image dockerd, same as the feature's dev-container
  manifest). `runAsUser: 1000` (vscode) + `runAsGroup`/`supplementalGroups:
[999]` (docker group - k8s drops the image's supplementary groups; the
  dockerd socket is `root:docker` 0660). `fsGroup: 1000` with
  `fsGroupChangePolicy: OnRootMismatch` (the default `Always` chowns the
  whole 50 Gi volume every pod boot).
- **PATH**: k8s `bash -c` skips login files, so the container command
  assembles the baked toolchains explicitly (nvm node glob, /usr/local/bin,
  py-utils, sdkman) before `exec docker-init.sh run.sh`.
- **`cache-init`** (root initContainer): creates the `.ci-cache/*` dirs,
  chgrp 999 + chmod **2775 setgid NON-recursively** (recursive over the
  multi-GB containerd store made every boot take minutes - the init never
  finished, the controller recycled the pod, jobs sat queued: the
  queue-stall incident), wipes `.ci-cache/docker/buildkit` (see the store
  pairing below), and `chown -R 1000:999` **the checkout tree only** (e2e
  bind mounts run as container root and write INTO the checkout; root-owned
  dirs are ununlinkable by the uid-1000 clean - at-boot scoping keeps the
  multi-GB caches out of the walk).

## The PVC (`shapea-cache-pvc.yaml`, atlas-shapea-cache, 50 Gi RWO PD)

One ext4 volume (PD - overlayfs works on it, NFS/Filestore would not),
subPath-mounted:

| Path (in pod)                       | PVC subPath            | Why                                                                                                                |
| ----------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `/opt/actions-runner/_work`         | (root)                 | work dir: runner `_tool`/`_temp` + job workspace (uid-1000-writable); the checkout under it is sanitized every job |
| `/var/cache/ci/{uv,npm,pre-commit}` | `.ci-cache/<name>`     | toolchain caches, OUTSIDE the checkout (the GitHub-hosted cache model)                                             |
| `/var/cache/ci/sops`                | `.ci-cache/sops`       | the sops key file (exists for sops; content irrelevant, key is in env)                                             |
| `/var/lib/docker`                   | `.ci-cache/docker`     | dockerd store: compose/e2e base images survive pods                                                                |
| `/var/lib/containerd`               | `.ci-cache/containerd` | **the critical one** - see below                                                                                   |

**Containerd's root must be volume-backed.** The image's
`/etc/containerd/config.toml` (root=`/var/lib/containerd`) + dockerd's
containerd-snapshotter (devcontainers/features#1642) mean every image/layer
snapshot lives under `/var/lib/containerd`, NOT `/var/lib/docker`. Left on
the pod root (the node's overlayfs), nested overlay mounts are rejected:
"failed to mount /tmp/containerd-mount…: invalid argument" killed every
e2e container and docker-build in trial run 40217828572.

**BuildKit metadata and containerd snapshots are a pod-scoped pair.**
`/var/lib/docker/buildkit` (metadata) references containerd snapshots by
id; if the metadata outlives the snapshot store (a pod that dies
mid-build, an infra change that moves one store - trial runs 40217828572 →
40219350705), every build dies "parent snapshot … does not exist". cache-init
wipes the metadata each boot; builds use `--cache-from type=registry`, so it
is disposable.

**The volume is deliberately NOT shared** with the (retired) Shape B cache:
two scale sets on one RWO disk = detach stalls + fsGroup chown flip-flop.

## Cache server (`actions/cache` for self-hosted)

Private repos get no `actions/cache` on self-hosted runners (GitHub's
service rejects them), so the tree used to stay warm on the work volume to
avoid paying install per job - which leaked root-owned dirs, staged
diagnostics and decrypted `.env` between runs. Now the tree is disposable
(ci.yaml, "Caches" below) and `ci.yaml` caches `node_modules`/`.venv` with
the stock `actions/cache` step against
[`github-actions-cache-server`](https://gha-cache-server.falcondev.io)
(MIT, `install.sh cache-server`, `cache-server-values.yaml`:
filesystem+sqlite on its own 20 Gi PD, 90-day cleanup, LRU at 90 %).

The contract has three parts - all three are required:

1. **The runner is the fork** (`.devcontainer/features/ci-runner`):
   stock `Runner.Worker.dll` hard-codes GitHub's results URL and ignores
   `ACTIONS_RESULTS_URL`; `falcondev-oss/github-actions-runner` is a
   drop-in (identical asset names, merges upstream) whose build honours
   `CUSTOM_ACTIONS_RESULTS_URL`. Verified: the string exists in the
   fork's v2.338.1 DLL, not in stock's.
2. **`CUSTOM_ACTIONS_RESULTS_URL`** on the runner container
   (`arc-shapea-values.yaml`) = the server's cluster DNS URL, trailing
   slash. The fork also skips runner self-update while it is set - a
   self-update would unpatch the binary and silently fall back to
   GitHub's central cache (no error, caching just stops). Runner version
   updates then become ours: bump the feature pin, rebuild the image.
3. **OIDC auth** (server default): the runner's job token is verified
   against `token.actions.githubusercontent.com` - per-repo cache scope,
   no shared secret. Non-cache traffic (artifacts) passes through to
   GitHub's results receiver, untouched.

## Caches (measured) - the tree is ephemeral on purpose

- `ci.yaml` checks out CLEAN (actions/checkout's default clean):
  node_modules, .venv, dist, coverage, e2e artifacts never leak between
  runs. The warm-tree experiment (runs 40225615871-40228013569) saved
  ~70s of install and caused a bug family - root-owned dirs from e2e bind
  mounts breaking checkout (EACCES rmdir), staged diagnostics surviving
  `git clean` and failing pre-commit - so it was retired: **caches
  persist, the tree does not**.
- `node_modules`/`.venv` via `actions/cache` → the cache server (above),
  keyed on the lockfiles. npm 47s / uv ~20s cold is the floor the cache
  restores are measured against.
- Validate (pre-commit) ~81s, e2e/docker base layers hit the containerd
  store - cache-driven (uv/PRE_COMMIT_HOME/containerd subPaths), none
  tree-driven.

## Rollback

`helm uninstall atlas-ci-shapea -n arc-runners` (+ `arc` in `arc-systems`),
delete `shapea-cache-pvc.yaml`, delete `atlas-arc-auth`/`atlas-ghcr-pull`.
The workflow side is a git revert of the ci.yaml flip (hosted runners
predate the variables, and the variables retired with Shape B).

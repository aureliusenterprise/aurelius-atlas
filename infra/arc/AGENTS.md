# infra/arc

ARC (Actions Runner Controller) deployment for running the `ci` job on GKE.
Not an Nx project - plain manifests + script, applied by hand from the dev
container (it bakes gcloud/kubectl/helm via devcontainer features).
Plan and phases:
[`docs/architecture/self-hosted-ci.md`](../../docs/architecture/self-hosted-ci.md).
Setup and the k8s contract: [`README.md`](README.md).

## Files

- `arc-shapea-values.yaml` - gha-runner-scale-set values: the job container
  IS the dev container image (privileged, in-image dockerd, work volume
  mounted at the runner root's `_work`, cache PVC subPaths).
- `shapea-cache-pvc.yaml` - PD (RWO) volume: work dir + toolchain caches +
  dockerd/containerd stores (README has the layout and the reasons).
- `install.sh` - subcommands: `cluster`, `controller`, `scale-set-shapea`,
  `cache-server`, `status` (`cluster` unused - target is the existing
  atlas-dev Standard cluster). Runner pods schedule on the default pool's
  headroom; there is no dedicated CI node pool (the Shape-B taint pool and
  the debug-era Ubuntu pool are both deleted).

## Conventions

- ci.yaml hard-codes `runs-on: atlas-ci-shapea`. The old `CI_*` flag-day
  variables (CI_RUNS_ON etc.) retired with the devcontainers/ci wrapper -
  do not reintroduce variable-selected runners.
- Image deploys: `CI_SHAPEA_IMAGE_TAG=sha-<full-sha> ./install.sh
scale-set-shapea` (the build workflow publishes the tag; helm `--set`
  redeploys the template). Idempotent after chart bumps.
- The pod is **privileged** (in-image dockerd); treat the container command
  and volumeMounts as one contract - README "What lives where" explains why
  each line exists (every one is a failed trial).

## Removal

`helm uninstall atlas-ci-shapea -n arc-runners` (+ `arc` in `arc-systems`),
delete the PVC + secrets, git-revert the ci.yaml flip. Nothing in
`.github/` hard-codes GKE beyond `runs-on:`.

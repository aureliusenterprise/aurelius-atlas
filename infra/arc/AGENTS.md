# infra/arc

ARC (Actions Runner Controller) deployment for running the `ci` job on AKS.
Not an Nx project - plain manifests + script, applied by hand from a machine
with `az`/`helm`/`kubectl`. Plan and phases:
[`docs/architecture/self-hosted-ci.md`](../../docs/architecture/self-hosted-ci.md).
Setup and flag-day: [`README.md`](README.md).

## Files

- `arc-values.yaml` - gha-runner-scale-set values (dind sidecar, taint/label
  to the CI node pool, resources, cache volume).
- `toolchain-cache-pvc.yaml` - Azure Files PVC backing `.container-cache`.
- `install.sh` - subcommands: `controller`, `nodepool`, `scale-set`, `status`.

## Conventions

- The repo-side flip is variables only (`CI_RUNS_ON`, `CI_DISK_CLEANUP`,
  `CI_USE_ACTIONS_CACHE`, `CI_CACHE_MOUNTS`) - never edit ci.yaml to move
  runners; delete the variables to revert to hosted.
- The dind sidecar is **privileged**; the `ci` taint + nodeSelector keep CI
  pods alone on that pool.
- After chart bumps, re-run `install.sh scale-set` (idempotent
  `helm upgrade --install`).

## Removal

`helm uninstall atlas-ci -n arc-runners` (+ `arc` in `arc-systems`), delete
the variables, delete the node pool. Nothing in `.github/` hard-codes AKS.

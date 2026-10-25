# Decision: self-hosted CI runners on GKE (ARC) vs GitHub-hosted

> **Status**: decision draft for review (thijs + colleague). 2026-10-25. Companion to [self-hosted-ci.md](<https://aureliusenterprise.github.io/feat-validate-job-in-devcontainer/architecture/self-hosted-ci/index.md>) (the how); this doc is the **should we**, with measured numbers. Nothing is provisioned yet.

## TL;DR

|  | GitHub-hosted (today) | Self-hosted on **existing** atlas-dev |
| --- | --- | --- |
| Money, 30-day volume (measured) | \~$0–37/mo (plan-dependent) | **\~$12/mo marginal** (pool + cache PVC) |
| Pipeline wall clock | green 18m34s | equal or better (warm caches, no 10 GB cache eviction) |
| Cache reliability | AFD outage broke builds (measured, Sep) | plain volumes, no third party |
| Queue / parallelism | shared pool, 5×8 GB pulls/jobs | own pool, jobs reuse a warm node |
| Ops burden | zero | ARC upgrades, GitHub App key, GHCR retention |
| Infra cost | — | **none new** - atlas-dev already pays the cluster fee |

**Recommendation**: proceed (Phase 1 canary on atlas-dev, \~1 day of work, fully revertible). At our volume the cost is a wash; we buy reliability, speed headroom, and independence. The old blocker ("needs a new Standard cluster, \~€70/mo") is void - atlas-dev **is** Standard mode.

## What we measured (30 days, 2026-09-25 → 10-25)

| Workflow | Runs | Runner-minutes |
| --- | ---: | ---: |
| CI (all jobs, pre-consolidation) | 250 | 3,567 |
| Publish Documentation (PR/main) | 327 | 446 |
| pages, Scan, image builds, deps-bots | \~120 | \~590 |
| **Total** | \~700 | **\~4,600** |

The consolidated CI job (PR 150) is **18m34s green** end-to-end; CI volume ≈ 250 runs/month, trending down with consolidation (5 jobs → 1 removes \~4×2m45s of setup per run: 250 × 11 min ≈ **46 runner-min/run saved** vs the old shape, already counted in the 18m34s).

## Costs

### GitHub-hosted (current)

Private repos, Linux runners: **$0.008/min**, included minutes per plan:

| Plan | Included | Overage/mo at \~4,600 min |
| --- | --- | ---: |
| Free (2,000 min) | 2,000 | **\~$21** |
| Team (3,000 min) | 3,000 | **\~$13** |
| Team + self-hosted | — | **$0** (self-hosted minutes are free) |

Non-money hosted costs, all observed by us this month:

- **Cache service outage** (Azure Front Door) returned HTML 400s and broke every `type=gha` docker build for hours - we rewired the layer cache to GHCR because of it. The Actions cache (uv/npm/pre-commit) is still the 10 GB LRU pool behind the same service.
- **Per-job overhead**: every job = fresh VM = 8.3 GB image pull (\~101 s warm) + cache restore + logins ≈ 2m18s; with 250 runs/mo ≈ **575 runner-min paid to setup alone** (the single-job shape already cut this 5×).
- **Queue**: PR jobs queue behind the shared hosted pool; burst PRs (dep bumps: 274 doc-publishes/mo show the fan-out) don't parallelise on demand.

### Self-hosted on GKE (marginal cost, atlas-dev exists already)

| Item | Europe-west1 est. |
| --- | ---: |
| CI pool: spot n2-standard-8, 0..3, scale-to-zero (250 × 18.5m ≈ 77 h/mo, \~$0.08–0.16/h spot) | **$6–12/mo** |
| Toolchain cache PVC: 50 GB pd-balanced | **$5/mo** |
| ARC controller (2 small pods on existing default pool) | \~$1/mo |
| GitHub App, ARC charts | $0 |
| GKE cluster fee | **$0 marginal** (paid today for atlas-dev, Standard) |
| **Total** | **\~$12/mo** |

Idle between runs: pool scales to 0; spot nodes are 60–91 % below on-demand. The dev-pool (3× e2-standard-4, \~$80/mo) is **not** charged to CI - it runs the atlas dev resources regardless.

**Break-even vs hosted: self-hosted is cheaper on Free (\~$21→$12), neutral on Team (\~$13→$12).** The case is the reliability/queue/overhead rows above, not the euro-centre.

## Why atlas-dev works (the correction)

The plan originally assumed we needed a **new Standard cluster** (\~€70/mo GKE control-plane fee), because an API check suggested atlas-dev was Autopilot (which forbids privileged pods - the ARC dind sidecar is privileged). That check was wrong: `autopilot: {}` (an **empty object**, which Standard clusters serialize) was read as "Autopilot". Verified now, three ways:

1. Console + `autopilot.enabled` field: **absent = Standard**.
2. Node labels: no `cloud.google.com/gke-autopilot` labels; pool is `default-pool` (Standard style).
3. **A real `privileged: true` pod scheduled and ran** on atlas-dev (Autopilot rejects it at admission).

So ARC lands on the existing cluster: a dedicated **spot CI node pool** (tainted `ci=true:NoSchedule` + nodeSelector - Standard supports both), the controller on the existing pool, a 50 GB PD cache PVC. No new cluster.

## Architecture (one paragraph)

ARC (`actions-runner-controller`, GitHub's official chart) turns each workflow job into an ephemeral pod. The job runs the **same pipeline, unchanged**, via `devcontainers/ci` on a per-pod privileged dind sidecar - the exact topology hosted runners use today (that's the bridge we merged: the composite action, `ci-pipeline.sh`, and the dev container need zero changes). The repo-side flip is **four variables** (`CI_RUNS_ON`, `CI_DISK_CLEANUP`, `CI_USE_ACTIONS_CACHE`, `CI_CACHE_MOUNTS`); delete them to revert. Full detail: [self-hosted-ci.md](<https://aureliusenterprise.github.io/feat-validate-job-in-devcontainer/architecture/self-hosted-ci/index.md>).

## Risks (honest list)

- **Privileged dind = root on the CI node.** Contained by: dedicated tainted spot pool, jobs are our own code (PRs are the exposure - a malicious PR runs privileged on a CI node, root of that node only; the dev pool is a separate node pool - not node-isolated from *data plane* blast radius of the same cluster, network policies + node separation are the mitigations). This is the same trust model every self-hosted-dind CI has.
- **Shared cluster**: CI pods share the control plane with atlas dev workloads. Worst case (runaway buildkit, node CPU): noisy-neighbour on the CI pool only; control-plane load from ARC is small.
- **Spot preemption** mid-run = failed job, requeues. Registry layer cache makes reruns warm. (Measured: zero evictions expected - CI is bursty.)
- **Ops ownership**: ARC chart upgrades, GitHub App private key rotation, GHCR `buildcache-*` retention (already a follow-up). \~a few hours/quarter.
- **Filestore API is blocked** in this project (billing-account service restriction): the RWX cache volume is downgraded to a 50 GB PD (RWO) for Phase 1 - serial canaries don't need RWX; Phase 2 adds one PD per node if parallel jobs land on separate nodes.

## Options

- **A - ARC on atlas-dev (recommended)**: \~$12/mo, revertible (delete variables + `helm uninstall`), no new infra. Phase 1 = canary workflow, 5 green runs, then flip.
- **B - Stay hosted** (status quo): zero ops, $13–21/mo, keep the AFD cache dependency and per-job pulls. Reasonable at current volume; the queue and 10 GB cache cap are the ceiling.
- **C - Dedicated Standard cluster**: the €70/mo scenario - unnecessary now (atlas-dev is Standard). Revisit only if CI's blast radius on a shared cluster becomes unacceptable.
- **D - Shape A later** (runner pod = the dev container image, no dind): removes the 8.3 GB per-pod pull (containerd caches per node) and the privileged sidecar. Phase 3, after A is boring.

## Decision asks

1. A vs B? (If A: we provision the tainted spot pool + ARC on atlas-dev, canary-only first - the hosted path stays live beside it.)
2. Who creates the **GitHub App** (org owner needed, Actions: read/write, this repo only)? Key goes into a k8s secret, never git.

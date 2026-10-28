# 019\. The system releases as one versioned whole

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

One version number, one changelog, one release event that publishes every deployable part. A released version is a complete, mutually consistent snapshot; parts are not independently versioned or released.

## Decision

**The system is the unit of release.** One version number, one changelog, one release event publishing every deployable part together. A released version is a complete, mutually consistent snapshot — every part in it was built and validated against the same everything.

**Parts move with the system, not beside it.** When a part changes, the system's version moves; the changelog records which parts moved and how.

This is the delivery face of two older decisions: the single repository makes one version meaningful ([001](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/001-single-monorepo/index.md>)), and the unit that ships is the unit that was validated ([010](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)) — lockstep release keeps those true at the moment of delivery, not only at the moment of commit.

## Context

The repository holds many deployable things — services, frontends, functions, connectors — useful only in combination: a frontend that speaks to a service that reads what a producer writes. The question is what gets a version number and a release: each part separately, or the system as a whole.

**Independent per-part versioning is what per-part packaging encourages, and it is paid for in compatibility knowledge.** Once parts move independently, "does this combination work?" has no cheap answer, and someone — usually the person deploying, usually late — becomes the source of truth about which versions belong together. The matrix of tested combinations grows faster than the team that must reason about it.

**Whole-system release is affordable only because of how the repository is arranged**: everything lives together and is validated together ([001](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/001-single-monorepo/index.md>)), so every commit already represents a consistent whole, and the pipeline builds every deployable part as one flow ([010](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)). Given that, per-part release adds a choice the organisation has no evidence to make wisely — it did not test the combination a partial release creates.

The team is one multi-disciplinary group: no second team with its own cadence to accommodate, no consumer taking one part without the rest. The cost of lockstep — a changed part releases only when the whole does — is a cost this organisation does not pay, because the whole always moves anyway.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One identifier for a state of the system.** "Deploy 4.4.0" is a whole instruction; "which parts?" is not a follow-up. |
| **R2** | **What ships was validated as a whole.** No release creates a combination that was never validated. |
| **R3** | **History is one story.** A single chronological changelog — no cross-referencing per-part ledgers. |
| **R4** | **Rollback is one move.** Deploy a previous snapshot, not reconstruct a compatible set of part versions. |
| **R5** | **Delivery is one event.** A version is fully available or not released — no half-released state. |
| **R6** | **Cheap to keep true.** One action by the release owner; the version derived from recorded change history, not hand-set. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Independent per-part versions | R2: every combination becomes a candidate, most untested. R3/R4: "what changed" and "roll back" become matrix questions. Right shape for a platform with unrelated consumers of parts — this system has none, and the cost lands on the deployer regardless. |
| Train releases (parts free, bundles scheduled) | R2 and R4 at bundle level, R1 not while two identifiers both describe what is deployed. R6: the train needs a curator to decide membership — the compatibility judgement lockstep avoids. Ceremony around a train that leaves whenever anything changes. |
| Release only changed parts per event | R1 and R3, and shorter pipelines tempt. R5: a version becomes a partial publication, and "deploy 4.4.0" quietly means "4.4.0 plus whatever the unchanged parts were last time" — a combination defined by deployment history, not by the release. |
| Do nothing (hand-tags, ad-hoc publishing) | R6: every release is manual and every missed step is a half-released state (R5). R3: a changelog written by hand at release time drifts from what changed. |

## Tradeoffs

### What it buys

- One number answers "what is deployed?" and "what changed?" (R1, R3).
- Every shipped combination was built and validated as one flow (R2) — the confidence transfer of [010](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>) extended to the whole system.
- Rollback is a single move (R4); releasing is one action (R6).

### What it costs

- An unchanged part still gets a new version number — noise to anyone who expects a part's version to track its own history; **the changelog has to carry that meaning instead.**
- A release waits on the slowest part to clear the gate (the shared set of checks every change must pass, [014](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)).
- The version is coarse: "4.4.0 → 4.5.0" says the system moved, not which parts did — a real loss for anyone consuming one part's history.

### Watch

- The changelog is the one place the per-part story lives: release notes that name affected parts are a standing obligation, not a courtesy.
- A release event that fails partway is exactly the half-released state R5 rules out: a version counts as released only when the whole event completes; a failed event is re-run to completion or abandoned, never partially claimed.
- R4's rollback is a deploy-time move onto a previous snapshot — today, deploying a previous release by hand until a mechanism makes it one move.
- A part that gains a consumer outside the system (a library published for general use) steps outside this record and needs its own versioning decision.
- Where "deploy one version" meets the environment — promotion between environments — this record stops: the settings record ([018](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) carries on, and the environment boundary belongs to [024](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>).

> [!NOTE]
>
> **Why release parts that didn't change?**
>
> Because a release is a snapshot, not a diff. Publishing only changed parts makes "4.4.0" shorthand for a combination assembled from deployment history — the matrix returns through the back door. An unchanged part shipping a new number is the visible price of a version that always names one validated whole (R2, R5).

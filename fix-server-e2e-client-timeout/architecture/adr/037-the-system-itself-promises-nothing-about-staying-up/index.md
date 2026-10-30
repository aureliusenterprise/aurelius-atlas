# 037\. The system itself promises nothing about staying up

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Availability is not a property the system carries — it is a property the adopting deployment builds around it. The system promises no uptime of its own: it must not fake availability, and it must not prevent it.

## Decision

**Availability belongs to the deployment, not the system.** The system promises no uptime of its own, and the rule has two halves: **it must not fake availability** — no page, guide, or example may claim resilience the arrangement does not provide — and **it must not prevent availability** — a part holds no private state that would pin it to one instance, and state that must exist lives in named stores a deployment can protect.

What the system *does* promise about loss and downtime is the recovery promise, owned by [026](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>) — not a prevention promise.

This decision was in force before it was written down: every part runs as an instance a deployment can multiply, the state the system keeps sits in stores a deployment can name and protect, and nothing claims an uptime no mechanism backs. **What this record adds is the posture in words, so that the absence of a cluster reads as a decision rather than an omission.**

## Context

People who meet the system ask, directly or by implication, how safe it is to depend on: what happens when a machine fails, whether a service can be lost for an hour, whether data survives.

The honest answer today is that the system, as built, provides no protection of its own — every part runs as a single instance, and the arrangement is deliberately small. That answer is reasonable for what the system is: an arrangement validated whole on one machine ([006](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), meant to be deployed inside infrastructure the adopting organisation already operates.

**The risk is not the smallness; it is the ambiguity around it:**

- A reader who finds guidance about replicating services can mistake advice to a future deployment for a property of the system.
- A reader who finds no statement at all can assume protection exists and build on it.
- A reviewer of the next design can read the missing cluster as an oversight and add machinery nobody asked for.

Each of these costs more than the missing sentence. The forces pull two ways: stating "no availability promise" plainly is honest but can be read as permission to ignore resilience; promising resilience the system does not have is worse — **it moves the failure from the machine to the trust.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The posture is stated, not inferred.** "Is this resilient?" is answered in a record, not in the silence between a single-instance arrangement and a replication tip. |
| **R2** | **No claim without a mechanism.** No document, guide, or example presents protection the system does not provide. |
| **R3** | **Nothing quietly prevents protection.** A part can run in more than one instance, or be replaced while down, without losing the thread — no private state only it can recover. |
| **R4** | **State is enumerable.** The state the system keeps lives in stores a person can list — what makes a deployment's protection decisions, and [026](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>)'s promises, possible. |
| **R5** | **The development arrangement stays honest about itself.** One instance of everything on one machine is a decision about where the system is built and validated, not a claim it can't run otherwise. |
| **R6** | **Advice to a deployment is marked as advice.** Guidance about replicating or protecting services reads as a recommendation to whoever deploys, not a property of what is deployed. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Promise availability now: cluster everything | R5 and the arrangement the whole-system record requires ([006](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) — a cluster cannot be the daily development environment. It buys prevention the organisation has not asked for, at a price every run pays. |
| Say nothing (the status quo) | R1 by definition; R2 by omission: silence is where an unbacked claim gets read in, and where the missing cluster gets "fixed" by someone who never saw the decision. |
| Per-part availability tiers | R6's purpose at this scale: with one team and one arrangement, a catalogue of tiers is upkeep answering a question nobody has yet asked differently for two parts. |
| Fold the question into recovery alone | "We don't prevent, we recover" is half the answer, recorded in [026](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>). R3: recovery of a store says nothing about whether a part can be multiplied or replaced — the prevention half. |
| Do nothing | Free today; fails every requirement the way the status quo does, by leaving the posture to be guessed. |

## Tradeoffs

### What it buys

- The missing cluster is a recorded decision, so reviewers protect it instead of "fixing" it (R1, R2).
- The deployment team gets an honest starting point: the list of stores to protect, and the knowledge that parts can be multiplied (R3, R4).
- The development arrangement is freed from being read as a production topology (R5).

### What it costs

- The system cannot win a requirement that demands built-in uptime, and the record says so plainly.
- "The deployment owns it" transfers risk to a decision the adopting organisation has not always made yet — which makes this record a prerequisite for [024](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>) to answer well.
- R3 is a standing constraint on every future part: cheap per part, real in aggregate.

### Watch

- The placeholder page on high availability under the architecture section remains a heading until written from this answer — **as advice to a deployment, per R6**, and the replication advice in the design guidance should be marked as such.
- The recovery promise this record points at is itself Proposed ([026](<https://aureliusenterprise.github.io/fix-server-e2e-client-timeout/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>)): until it is accepted, **the system promises neither prevention nor recovery**, and that gap is stated here rather than papered over.
- A part that begins holding private state a restart cannot recover is a deviation from R3 that belongs in this record's follow-ups until removed.

> [!NOTE]
>
> **Isn't 'no availability promise' permission to ignore resilience?**
>
> It reads that way, and that reading is the record's named risk — R6 marks deployment guidance as advice precisely so the honest answer is not a shrug, and R3 makes the system *enable* resilience even while not promising it. What the system refuses is the unbacked claim: a promise with no mechanism moves the failure from the machine to the trust.

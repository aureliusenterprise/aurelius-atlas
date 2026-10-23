# 011\. The development environment is a versioned artifact

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

The environment developers and the pipeline run in is built from a definition in the repository. One base for every machine; machine differences stop at its boundary.

## Decision

**The development environment is a versioned artifact, not a local arrangement.** It is built from a definition in the repository, carries the toolchains, runtimes, and CLIs the work needs, and is the same on every machine — **one base, not a variant per OS**.

The definition is authoritative: a rebuild reproduces it, and a running instance carries no state the definition cannot reproduce. When the work needs a tool, the change is an edit to the definition, not a step performed on machines.

## Context

The tooling runs on machines the organisation does not fully control: laptops, CI runners, occasionally an engineer's workstation. The developer machine is the least controllable of these — people have their own machines, and each drifts: tools at assorted versions, paths assumed, utilities installed by accident. None of these is a decision, and the automation that runs against the estate discovers each difference, one at a time.

Left unmanaged, the automation adapts to the estate, spending effort on the estate instead of the system. The pipeline has no keyboard: it cannot do the machine preparation the tooling assumes. The difference between two machines becomes a difference the automation must carry.

> [!NOTE]
>
> **The base image ships nothing — why govern it at all?**
>
> Because every claim the system makes is produced inside it. The base is the tool that produces and validates the shipped unit, not a deliverable and not the unit [010](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>) governs — a change to it is not a release. What the record rules is its honesty: built from the definition, rebuilt on a stated trigger, one base for people and CI, so "works in the base" means works everywhere the work runs.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One base, people and pipelines.** People and CI work in the same environment — a result in one is a result in the other. |
| **R2** | **Machine differences stop at the boundary.** What a person's machine has, lacks, or is at some version stops affecting the work at the base. |
| **R3** | **Built, not inherited.** Assembled from a definition in version control; reviewable with the change that needed a tool; rebuildable. |
| **R4** | **Unattended runs need no person.** A clean machine runs the automation unattended; "set up your machine" is not a precondition. |
| **R5** | **A tool is a reviewed edit.** Adding a tool changes the definition, reviewed with the change that asked for it. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| A documented machine standard | R2: a checklist covers what its author thought of; machines drift from it within weeks; the automation discovers the differences. R4: preparation is a person's task. |
| A variant per operating system | R1: the base is no longer one thing, and the automation carries the variants — conditionals per platform, multiplied across the estate. |
| Rely on tools the machine already has | R1: the base becomes the union of every machine's accidents; automation carries conditionals for machines that differ. R2/R3: nothing is declared; a clean machine has none of it. |
| Do nothing (everyone sets up their own) | R1 by default: every machine is its own environment, and "works on my machine" is a claim about one machine. R4 by default: unattended runs inherit whoever set the machine up. |

## Tradeoffs

### What it buys

- The automation is written once, against the base (R1).
- Machine differences stop at the base (R2).
- A clean machine runs the work with one command — which is what makes unattended CI and the offline laptop work (R3, R4).
- A tool is added by a reviewed edit (R5).

### What it costs

- The base is a maintained artifact; a stale base produces failures that look like application bugs.
- The base sits in every delivery path: a base-build failure stops work for everyone, not one machine.
- Tooling that cannot run in the base is excluded from the work — it needs a stated arrangement, not an ad-hoc one.

### Watch

- The base is currently a container image; replacing the form changes the follow-through, not the rule. [010](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>) governs the shipped unit, not the base.
- Rebuild the base on a stated trigger: drift between the definition and a running environment is the difference this record exists to remove.
- Where a part runs outside the base — the build tool, an emulator invoked directly — that part deviates.
- The base is a tool for producing and validating the unit, not a deliverable: a change to the base is not a release (see [010](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)).

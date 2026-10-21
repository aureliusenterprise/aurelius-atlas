# 001\. Keep one monorepo for every stack

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

All first-party work — every language, application, library, and piece of development infrastructure — lives in one repository run by one task runner, so a cross-stack change is a single atomic commit. Modules leave as whole slices; the repository itself never splits.

## Decision

**One repository, one task runner.** The runner understands each toolchain natively, so build, test, and run have one entry point everywhere.

**A change that crosses a technology boundary must remain possible as a single reviewable, atomic commit.** Modules may be removed wholesale ([002](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/002-modules-are-removable-slices/index.md>)); the organisation will not split what remains into separate repositories.

## Context

The organisation delivers one business system across several stacks — interface, backend services, shared libraries, and the infrastructure that runs them — and its capabilities only pay off end to end: a shared business concept, a customer or an order, is realised from the screen through the services into storage.

The business situation:

- **One multi-disciplinary team** delivers work, so a single feature routinely touches several technologies at once.
- **The team is small:** everyone shares the libraries, workflow, and docs; nobody owns a single technology.
- **New joiners must understand how the pieces fit**, not bootstrap a setup.
- **Releases follow business milestones,** so a shared-concept change lands everywhere at once.

The decision is how many sources of truth the delivery path has — one place where code and workflow live, or several. The cost of getting it wrong is paid for years afterwards, in every review spanning a boundary and every release needing coordination — by the people making the changes, not by whoever chose the layout.

## Requirements

Any acceptable layout must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Atomic cross-stack change.** A shared-concept change ships as one unit, no coordinated releases. |
| **R2** | **One way to run the system.** One entry point for build/test/run, learned once by onboarding and CI. |
| **R3** | **Coherence at small-team cost.** Shared code, workflow, and docs stay consistent as they evolve. |
| **R4** | **One place to learn the system.** A new developer browses the whole system in one place. |
| **R5** | **Ownership matches staffing.** Boundaries reflect one multi-disciplinary group, not imaginary teams. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Repository per technology (polyrepo) | R1: a shared-concept change becomes multi-repo release coordination with windows where parts disagree. R3: workflow and docs duplicated per repo. R4: a joiner inherits repos plus the wiring between them. |
| Folders with no unifying task runner | R2: "run the whole system" has no answer — the everyday question for a joiner or CI. R3: every toolchain's workflow re-invented, re-maintained. |
| Do nothing (each technology keeps its own repo) | R1, R3 by default: shared code and docs drift between the parts; a joiner receives pieces, not a working whole. |

## Tradeoffs

### What it buys

- Cross-stack changes are atomic and reviewed once (R1).
- The workflow is defined once and applies everywhere (R2, R3).
- A new developer follows one business concept end to end without leaving the repository (R4).

### What it costs

- The repository carries tooling for several ecosystems, and every toolchain decision must coexist with the others.
- Checkout and CI cost grows with everything included.
- No repository-level access boundary: module discipline is a convention, not a wall.

### Watch

> [!NOTE]
>
> **What stops the monorepo from rotting?**
>
> Two compensating rules, each with its own record: modules removable as whole slices ([002](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/002-modules-are-removable-slices/index.md>)) and documentation colocated with what it documents ([003](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/003-every-project-documents-itself/index.md>)). The wall is not enforced by repository boundaries, so these conventions are the enforcement.

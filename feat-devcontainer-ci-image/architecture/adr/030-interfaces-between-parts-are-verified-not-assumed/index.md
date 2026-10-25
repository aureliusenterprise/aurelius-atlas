# 030\. Interfaces between parts are verified, not assumed

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Accepted 2026-10-19: for the catalogue's public interface, the checking mechanism is the parity harness — the agreement is stated once, in scenarios read from the reference source and cited ([052](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)), and drift fails the change (R1, R4). Internal interfaces are typed imports inside one repository ([001](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/001-single-monorepo/index.md>)), so consumers are not hand-mirrored (R2). Named gap: the template example frontend's hand-written TS mirror is unverified — a deviation that ends with the example's removal (DD-019); the Atlas dashboard is vendored and out of scope (R3).

Where a part offers an interface another consumes, the agreement is stated once and checked: a change that breaks a consumer fails where it is made, not where it is felt. The check remembers what the provider sends, so consumers do not have to.

## Decision

**The agreement is stated once, and a check enforces it.** Where one part offers an interface another consumes, the agreement between them lives in one place and is checked, so a change that breaks a consumer is caught where it is made, not where it is felt. A consumer does not rely on remembering what the provider sends — **the check remembers for it.**

The domain concepts behind these interfaces already have one canonical definition ([004](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/004-one-shared-domain-model/index.md>)); this record covers the interfaces themselves — the callable surface a consumer actually depends on.

## Context

The system's parts talk over interfaces: screens call services, services call services, and the shapes crossing those boundaries are the business concepts. An interface is a promise in both directions — the provider promises what it returns, the consumer promises what it sends — and **a promise only one side wrote down is a promise nobody enforces.**

Right now each side writes its own version. The provider declares what it serves; the consumer re-declares by hand what it believes the provider serves. Nothing compares the two. The provider publishes a machine-readable description and a test confirms it exists — but nothing downstream reads it, so **the description can say one thing while the consumer assumes another, and both are green.**

That is the shared-domain-model failure ([004](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/004-one-shared-domain-model/index.md>)) one layer out: a concept can be canonical and still be transported wrongly, because the transport agreement is folklore on both sides.

The cost lands predictably: a provider renames a field, changes a type, makes it absent — every consumer that assumed the old shape keeps compiling and starts failing at runtime, in a screen a person is looking at, far from the change. More consumers, more copies, more coordination exercises per change.

**One fact makes fixing this cheap here:** every consumer lives in the same repository as the provider it reads ([001](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/001-single-monorepo/index.md>)), so finding them is a search, not a campaign. The arrangement that makes interface verification expensive in a distributed estate is absent — which is why these requirements are worth meeting at the cheapest point, before the estate grows.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The agreement is stated once.** One place says what the interface is; provider and consumer both answer to it. |
| **R2** | **Drift fails the change that caused it.** A check at commit or review time, not a runtime discovery. |
| **R3** | **Consumers are found, not remembered.** Dependents identifiable mechanically; "did we get everyone?" has an answer. |
| **R4** | **The agreement is readable by whoever integrates.** What it accepts and returns, without reading provider source. |
| **R5** | **Compatible change stays cheap.** An optional element costs a small step, not a regeneration ceremony. |
| **R6** | **The check is honest about what it covers.** An unchecked interface is named as unchecked — no false confidence. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Hand-mirrored interfaces (status quo) | R1 by construction, R2 completely: nothing compares the two statements, so drift is invisible until runtime. R3: finding consumers means searching for copies of a shape and hoping the search was clever enough. |
| Generate consumers from the provider's description | R1, R3, R4, R5 elegantly. R2 on its own: generation proves the consumer matches the description, not that the provider honours it. R6 fails unless the description is a contract with teeth, not documentation with a syntax. Assumes every consumer tolerates a generated shape — a user-facing interface often won't. |
| Contract tests between the sides | R2 and R6 directly; survives a provider that won't publish a description. R1 as usually practised: expectations live in consumer tests, so the agreement is written N times. R4: a test suite is not a document an integrator can read. |
| Coordination by review | R2 and R3 exactly as often as reviewers are new, tired, or far from the other stack — which, in a system spanning several languages on one machine ([006](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), is often. The current arrangement with a title. |
| Do nothing | Keeps every interface change a runtime discovery. R1–R4 by leaving the agreement unwritten and unchecked — the state described as an option. |

## Tradeoffs

### What it buys

- Interface breakage moves from user screens to the change that caused it (R2).
- Consumers of a change are enumerable rather than remembered (R3).
- Integrators get a readable statement instead of an archaeology project (R4).
- The shared-concept decision finally covers how concepts travel, not only what they are.

### What it costs

- The agreement becomes a maintained artifact — and **a stale agreement is worse than none, because it is trusted.**
- Generation trades hand-written consumer code for generated code that must be lived with; user-facing shapes resist being generated.
- Enforcement needs a checking point; the accepted mechanism (the parity harness, R1/R4) covers the public interface, and the remaining gap is named below rather than papered over.

### Watch

- The provider's machine-readable description and the test that only confirms it exists are the seed for a comparison check where the parity harness does not apply (R6).
- Which representations are generated versus hand-kept ([004](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/004-one-shared-domain-model/index.md>)) is answered here for interfaces only; how an interface changes without breaking readers is governed by [017](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/017-shared-concepts-change-only-compatibly/index.md>) — this record adds verification, not direction. How the concepts travel over streams — ordering and duplication — is owned by [027](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/027-every-stream-carries-a-stated-delivery-guarantee/index.md>); the streaming slice left with the catalogue's scope ([050](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)).

> [!NOTE]
>
> **Why is a published OpenAPI description not enough?**
>
> A description that nothing compares against is a claim, not a check. The provider can publish a description that disagrees with its own code, and a consumer's hand-written mirror can disagree with both — all green (R2). The check must compare provider-against-statement and consumer-against-statement; publishing one side's belief is step one, not the mechanism.

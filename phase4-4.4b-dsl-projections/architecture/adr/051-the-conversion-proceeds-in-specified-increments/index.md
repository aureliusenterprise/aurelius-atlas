# 051\. The conversion proceeds in increments, each defined by a written specification

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Aurelius Enterprise

The catalogue is converted in increments: one reviewable change, one named behaviour, one written specification that comes before the code. An increment is not complete until its rules are tested, its parity checks pass, and its decisions are recorded.

## Decision

**Increment, spec, code — in that order.** The conversion proceeds in increments. Each is one change of reviewable size that ports one named behaviour, and it begins with a short written specification of that behaviour: scope, rules with identifiers, origin in the old system, deviations, and acceptance.

**Definition of done.** An increment is not complete until its rules are tested, its parity checks pass, and its decisions are recorded.

## Context

- **A big-bang rewrite cannot be reviewed** — and a review that cannot be done becomes a signature without understanding ([044](<https://aureliusenterprise.github.io/phase4-4.4b-dsl-projections/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)).
- **The old system is large** and its behaviour is spread over many classes.
- **Without a stated scope per change**, reviewers cannot tell an omission from a decision, and the project cannot tell how far it has come.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Reviewable size.** A reviewer can understand one change in one sitting. |
| **R2** | **Stated meaning.** What a change is supposed to do is written down before it is judged. |
| **R3** | **Measurable progress.** At any moment it is clear which behaviours are done. |
| **R4** | **Decisions travel with the change.** The reasons for a change are recorded in the same change, not reconstructed later. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Big-bang rewrite, reviewed at the end | R1 and R3. |
| Increments without written specs | R1; R2: the code becomes its own specification, and review checks consistency, not intent. |
| Feature tickets in an external tracker | Partly meets R3; R4: the reasoning lives outside the repository and is lost with the tracker. |

## Tradeoffs

### What it buys

- Every change has a stated purpose and an objective definition of done; progress is visible in the repository itself.

### What it costs

- Writing a specification takes time before any code exists.
- Splitting large behaviours into increments occasionally needs temporary scaffolding.

### Watch

- The roadmap, specification template, and design log live in [the conversion ledger](<https://aureliusenterprise.github.io/phase4-4.4b-dsl-projections/architecture/conversion/index.md>); the pull request template asks for the increment and the records it touches.

> [!NOTE]
>
> **Why specify before coding, when the spec may be wrong?**
>
> Because the spec is where a reviewer can object cheaply: written rules with identifiers can be argued with, tested, and cited (R2), while a merged implementation argues by existing. A spec that turns out wrong is amended in the open; an implementation that was silently wrong is found in production.

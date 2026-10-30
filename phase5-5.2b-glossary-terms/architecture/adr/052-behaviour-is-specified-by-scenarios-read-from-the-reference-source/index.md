# 052\. Behaviour is specified by scenarios read from the reference source, without running the reference

- **Status:** Proposed (becomes Accepted when increment 0.4 provides the scenario harness)
- **Date:** 2026-10-17
- **Deciders:** Aurelius Enterprise

Supersedes [048](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>).

A ported behaviour is accepted only when it passes scenarios whose expectations are read from the reference implementation's source and its own tests, each scenario citing where it was read. The reference is never built, run, or recorded from.

## Decision

**Scenarios, cited.** A ported behaviour is accepted only when it passes scenarios — requests with their expected responses — whose expectations are read from the source code and the own tests of the reference implementation, each scenario citing where it was read.

**No running reference.** No instance of the reference implementation is built, run, or recorded from.

**Scenarios are code.** They are stored with the code and reviewed like code; a comparison ignores only fields declared volatile, and a deliberate difference is declared with the deviation it belongs to.

## Context

The contract the new system must honour ([046](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)) is defined by a large existing implementation, not by a complete written specification. [048](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>) proposed recording the responses of a running reference implementation.

- **The goal is independence.** The conversion aims at a system that does not depend on the old one; operating the old system — even only to record from it — keeps a toolchain and an operational skill alive that the organisation wants to retire, and ties the work to building a large legacy codebase.
- **The source is enough.** The reference's source code, its own tests, and its documentation remain available and fixed at one version.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Grounded expectations.** Every expected response can be traced to a named place in the reference's source, tests, or documentation, so a reviewer can check it against something the implementers did not write. |
| **R2** | **Repeatable without the old system.** No test run, and no step of writing a test, needs the reference implementation built or running. |
| **R3** | **Changes to expectations are visible.** When what counts as correct changes, the change shows up in review. |
| **R4** | **Intended differences are explicit.** A deliberate deviation is declared with its recorded deviation, and the comparison respects it rather than being silenced test by test. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Record from a running reference (048) | The strongest oracle for R1; R2: someone must build and run the reference to record each new scenario. |
| Hand-written expectations, uncited | R1: the expectations encode the implementer's reading with nothing to check them against. |
| Run the reference's own integration tests against the new system | R1 for what they check; R2: their harness needs the reference's build — and they check too little of each response to protect the dashboard. |

## Tradeoffs

### What it buys

- No legacy toolchain in the loop; every expectation carries its evidence; everyday runs are fast and offline.

### What it costs

- Expectations encode our reading of the source, so behaviour that is hard to see in the code — serialisation details, ordering, error texts produced by frameworks — can be misread. **Review must compare a scenario with its citation**, and scenarios borrow the reference's own test fixtures verbatim where they exist.

### Watch

- Current reference: the `release-2.4.0` tag of Apache Atlas ([DD-001](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/conversion/design-log/#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served>)).
- The scenario format, runner, and comparison are test tooling; results appear in the published test report ([049](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>)).
- Shadowing production traffic of an existing Atlas remains possible later as a release check for a migrating customer.

> [!NOTE]
>
> **If nobody runs the old system, how do you know your reading is right?**
>
> You don't know it from a machine — you know it from citations a reviewer can check: every expectation names the place in Atlas's source, tests, or docs it was read from (R1), and the reference's own test fixtures are borrowed verbatim where they exist. That is a weaker oracle than a running system, accepted deliberately: the running system's cost is the legacy toolchain the conversion exists to retire (R2).

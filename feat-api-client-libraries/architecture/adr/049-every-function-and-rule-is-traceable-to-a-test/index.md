# 049\. Every function and every specified rule is traceable to a test, and the trace is published

- **Status:** Superseded by [056](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/adr/056-behaviour-is-proven-by-executed-tests-not-by-a-trace-gate/index.md>)
- **Date:** 2026-10-24
- **Deciders:** Aurelius Enterprise

Every public function and every specified rule must be named by a test, and the pipeline refuses a change that leaves either uncovered. Each change publishes one report showing, per rule and per function, which tests cover it and whether they passed.

## Decision

**Coverage means named by a test.** Every public function of the catalogue code and every rule in an increment's specification is named by at least one test; the pipeline refuses a change that leaves either uncovered.

**One published trace per change.** Every change produces one test report that shows, per rule and per function, which tests cover it and whether they passed.

## Context

The conversion produces a large amount of new code in a short time, much of it with machine assistance, and every change carries two human signatures ([044](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)).

- **Reviewers need to see what a change proves, not only what it contains.** A signature is only as good as the evidence in front of it.
- **Line coverage is not this.** It says that code ran during a test, not that any test meant to check it — and it says nothing about whether the specified rules were checked.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **No untested function.** A public function without a test that names it does not merge. |
| **R2** | **No unchecked rule.** A rule stated in a specification without a test that names it does not merge. |
| **R3** | **One place to look.** A reviewer opens one report per change and sees results, coverage, traceability and parity together. |
| **R4** | **Cheap to comply.** Declaring what a test covers is one line in the test. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Coverage percentage only | R1 and R2: incidental execution counts as coverage, and rules are invisible. |
| Manual traceability matrix | R1 and R2 in practice: the document drifts from the code on the first busy week. |
| Naming conventions (test name contains function name) | Partly meets R1; fragile under renames, and it cannot express rules or several functions per test. |

## Tradeoffs

### What it buys

- Reviewers get evidence instead of assurances; gaps are found by the pipeline, not by users.
- The report doubles as living documentation of what is done.

### What it costs

- Every test carries a declaration, and trivial functions still need a named test.
- The check can be satisfied by a weak test, so review of test quality remains a human job.

### Watch

- Current implementation: a pytest marker `covers`, a checker run in the test pipeline, and an HTML report built from JUnit and coverage results.

> [!NOTE]
>
> **Doesn't a declaration-only marker invite gaming?**
>
> It does — the record accepts that openly: the check proves a test *names* the function, not that the test is strong. Test quality stays a review judgement (R1, [044](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)). The marker's job is to make silence impossible: an untested function is visible as an absence, which line coverage hides.

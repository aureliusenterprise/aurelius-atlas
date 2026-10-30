# 056\. Behaviour is proven by executed tests, not by a trace gate

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Aurelius Enterprise
- **Supersedes:** [049](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>)

The pipeline proves a change by running its tests — unit, parity scenarios, end-to-end — and nothing else. It no longer gates a merge on a traceability check, and it publishes no per-change trace report. Naming what a test covers stays a code-review convention: the `covers` marker and the trace tool remain, as a local aid.

## Decision

**Executed behaviour is the gate.** A change merges when its tests pass; the pipeline refuses a change that fails a test, not a change whose coverage markers have gaps. The desired behaviour of the catalogue is encoded in the unit, parity, and end-to-end suites, and those executed results — with the coverage gate ([ADR 015](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)) — are the evidence a reviewer signs against.

**The trace stays as a convention, not a gate.** Tests keep naming what they prove via `@pytest.mark.covers`; reviewers use the names to find the test behind a rule. `aurelius-atlas-trace check` and `report` remain local tools, run by whoever wants their answer. The pipeline runs neither.

## Context

[ADR 049](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>) (increment 0.3) required every public function and every specified rule id to be named by a collected marker, with the pipeline refusing gaps and publishing one trace report per change. In practice the requirement duplicated what the suites already prove: the desired behaviour of each increment is encoded in its unit tests, which run on every change, while the check proves only that a test *names* a target — a declaration, collection-only, never an executed result. Keeping the declaration true across the whole surface (TypeScript citations, end-to-end claims, cross-project rules) consumed pipeline stages and review attention without adding evidence, and its gaps surfaced as CI noise rather than as missing tests.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Executed proof.** What blocks a merge is the result of running tests, not files. |
| **R2** | **No duplicated proof.** One place states what a test is for; bookkeeping on top is noise. |
| **R3** | **Reviewable evidence.** A reviewer sees, in the change, the tests and results behind it. |
| **R4** | **Cheap convention.** Naming what a test proves stays available and does not block. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Keep the gate as specified (049) | R1: the check proves naming, not behaviour; R2: it restates what the unit tests already encode. |
| Widen the gate (citations for TypeScript, e2e) | R2: more mechanism proving the same declarations, more pipeline and review cost, still no executed result. |
| Manual traceability matrix | 049's own objection: the document drifts from the code on the first busy week. |
| Drop the marker convention as well | R3: reviewers lose the pointer from a rule id to the test that proves it. |

## Tradeoffs

- **Positive:** the pipeline is smaller and says only what it can prove — a failed test; no marker bookkeeping blocks a merge; the suites stay the single source of intended behaviour.
- **Negative:** an untested function is no longer surfaced as a pipeline gap; coverage percentage (the SonarQube gate) and review are what catch it. The per-change published trace report is gone.
- **Neutral / follow-ups:** parity scenarios keep their citation discipline ([ADR 052](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)) — that is how expected behaviour is justified, and it is unchanged. The trace lib stays for local use and is removable as a slice when the convention fades.

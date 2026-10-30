# 014\. The gate that refuses a change is defined once

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

The checks that gate a change are defined in exactly one runnable place, and the pipeline runs that same definition. What refuses a commit refuses a merge.

## Decision

**One definition, run at two moments.** The gate — formatting, linting, typing, secret scanning, file well-formedness — exists once, as an artifact that can be run. The person committing runs it; the pipeline runs the same thing, not a second list written for it.

**A rule cannot exist in one moment and not the other.** Adding a rule is a single edit effective at both. Checks too expensive for the everyday moment (full suites, builds) run in the pipeline and are **named as pipeline-only**, not absent from the local gate with no mention of why.

This record settles where the gate is written and how often it runs; which findings it blocks is decided elsewhere ([015](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)).

## Context

Every shipped change passes two moments of validation: the moment a person commits, the moment the pipeline reviews before merge. Both need the rules; the question is how many times the rules are written down.

**Two written lists drift apart by their nature.** A local script and a pipeline definition start identical and end apart, because whoever adds a rule usually thinks of one place. The drift costs in two ways:

- The person whose change passes the first moment and fails the second pays a round trip through a pipeline run, and the lesson learned is that local passes mean nothing.
- A gate discovered late trains people to treat the pipeline as the adversary rather than as evidence.
- The team is small and multi-disciplinary: the people maintaining the rules are subject to them, so a rule kept in two places is maintained twice — which is how rules become inconsistent and then distrusted.
- The repository spans several stacks: a gate defined per stack is several lists with several gaps, and the gap is where the next defect lands.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One definition of the gate.** The rule set exists once, as a runnable artifact — no second list kept in step by memory. |
| **R2** | **No rule discovered only in the pipeline.** Passing locally means passing there, except checks explicitly named pipeline-only. |
| **R3** | **Cheap to keep true.** A rule is one edit by the person who wants it, effective at both moments. |
| **R4** | **The gate is reviewable.** The rule set is versioned, so a change to what is enforced is visible as a change. |
| **R5** | **Every stack is inside the gate.** One definition covers every technology, so no stack is silently ungated. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| The pipeline as the only gate | R1 and R4 pass, R2 fails by construction: every rule surfaces at its most expensive moment, after review time is spent, and the repair loop is a commit plus a run. It also lets bad form into history and complains afterwards. |
| Two hand-maintained lists | R1 outright, R3 with it: the lists are maintained by whoever remembers both, which over time is no one, and the drift is invisible until a change is caught in it. |
| A gate per stack, wired per project | R5: the gate becomes the union of what each stack adopted, and a new stack starts ungated. R3: a rule added "everywhere" is N edits. |
| Do nothing (rules live in review comments) | R1 by default: the rules exist in whoever reviews pull requests. R4: enforcement is a person's mood, and consistency scales with the reviewer's stamina. |

## Tradeoffs

### What it buys

- A person who can commit can merge — the pipeline adds no surprises of form (R2).
- A rule is one edit that lands everywhere at once (R1, R3).
- The rule set is a reviewed artifact: relaxing or tightening enforcement is visible history (R4).
- Every stack enters the same gate (R5).

### What it costs

- The gate must run wherever people work, so its tooling must exist on every machine — a dependency on the versioned development environment ([011](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/011-the-development-environment-is-a-versioned-artifact/index.md>)), not on what a machine happens to have.
- The gate must stay fast enough to run before every commit, or people start bypassing it. **Gate runtime is a constraint to defend.**

### Watch

- The pipeline-only checks are a standing exception that must stay named: a check that becomes cheap belongs local, a check that becomes slow belongs in the pipeline — each a reviewed edit to the definition.
- The local gate runs against files a change touches; the pipeline runs it against the whole repository. A change to a shared rule (a lint config, a shared type) can pass locally and fail there: a **second named exception** to R2, not a hidden one. Whoever edits a shared rule file runs the gate across the repository before pushing.

> [!NOTE]
>
> **Why not let the pipeline be the authority?**
>
> Because it makes the cheap lesson expensive. A rule that fires only in the pipeline costs a commit, a run, and a context switch — and teaches that local green means nothing. Moving discovery to commit time is the whole point of defining the gate once.

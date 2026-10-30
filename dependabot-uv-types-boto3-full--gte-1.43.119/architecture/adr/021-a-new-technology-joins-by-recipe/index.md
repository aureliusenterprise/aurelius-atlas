# 021\. A new technology joins the system by recipe

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

A technology the system did not use arrives by a written, repeatable recipe, not hand-wired plumbing. One pass makes it discoverable, buildable, gated, releasable — and removable.

## Decision

**Admission is a recipe.** When a new language, artifact kind, or class of service takes root, it arrives by a repeatable written procedure that makes it a first-class citizen in one pass. A complete recipe does four things:

- **Recognition:** the workspace learns to see projects in the technology by the markers they carry — discovered, not registered.
- **Lifecycle:** the standard build, validate, package, run — through the same task runner, so pipeline, hooks, and people see one way to do things.
- **Bring-up:** its development infrastructure starts with the application, as every project kind already does ([005](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/005-dev-infra-starts-with-the-app/index.md>)).
- **Removal:** the checklist is recorded at admission — what to unwire, where, in which files.

**The recipes live beside the directories they govern** and are followed by whoever adds the project, human or automated agent. Recognition logic is workspace-level and shared, not per-project. This record decides how a technology is admitted; what the repository says to whoever works there afterwards is governed elsewhere ([022](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)).

## Context

The system is deliberately polyglot — a browser application, services in several languages, functions, connectors, pipelines, documentation — and polyglot means many kinds of thing must be built, run, and released.

The task runner is the single entry point: one command shape for every project, so the workspace-wide flows — the gate (the shared set of checks every change must pass, [014](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)), and the release — reach everything without per-project wiring.

**The pressure point is the moment a new kind of thing arrives.** Without a recipe that moment produces bespoke wiring: a task definition copied from a neighbour and adapted, a pipeline step added by hand, a compose file with no owner, a discovery list someone must remember. Each choice is small and defensible; together they are how a workspace silently becomes N ways of doing the same thing — and how a technology becomes **unremovable**: nobody knows everything that was wired for it, so nobody dares take it out.

> [!WARNING]
>
> **The decay mode: unremovable by accretion**
>
> Bespoke wiring accumulates invisibly: each copy-adapt-add is defensible, and the whole is a technology nobody can leave. The recipe's removal notes are the counterweight — a technology is admitted with its exit path written, so "take it out" stays a job a person can do.

With a recipe the same moment is routine, and the knowledge is captured where the second project of that kind doesn't rediscover it. This matters more here than in a typical organisation: the people doing the adding are not always people — automated agents make changes in this repository, and a written recipe is something an agent can actually follow. The marker-keyed recognition mechanism already exists for the technologies in use; this record makes it the permanent way in.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Discovered, not registered.** A project in an admitted technology is picked up by what it contains; forgetting to announce it is impossible. |
| **R2** | **One command shape covers every technology.** Build, test, lint, serve, release run the same in every language. |
| **R3** | **Admission is a written, repeatable procedure.** The second project costs less than the first; followable without oral tradition. |
| **R4** | **Gate and release include new technologies for free.** Opting in to validation is not a skippable manual step. |
| **R5** | **Every admitted technology is removable.** The removal checklist ships with the recipe; "we don't know what it's wired to" is ruled out. |
| **R6** | **Recognition logic is shared.** Detection and lifecycle live in one place per technology, reviewable once. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Hand-wire from a neighbour's example | R3: the knowledge lives in whoever copied what. R5: removal knowledge is never captured because wiring knowledge was never written. R2 only while everyone copies faithfully — which is what drift prevents. |
| Per-project registration lists | R1: forgetting the list is the default failure. Spends R3's budget on bookkeeping the marker mechanism makes unnecessary — the arrangement the current mechanism already replaced. |
| One language, no new technologies | The premise: the system's shape is settled and the right tool per job is the point. This alternative rejects the system, not the arrangement. |
| Native tooling orchestrated outside | R2: the command shape fragments by language. R4: workspace flows must learn each technology twice — to run it, to keep the external flow in sync. R5: external wiring is precisely what nobody can enumerate for removal. |
| Do nothing (no recipe, no shared recognition) | Free until the second technology arrives, then pays per project. Fails R1–R5 by drift rather than by decision — the worst way to acquire them. |

## Tradeoffs

### What it buys

- A new technology is buildable, gated, releasable, and removable on day one (R2, R4, R5).
- "How does a thing of this kind join us?" is written once, followable by agents as well as people (R3).
- Recognition is a property of the project's own files (R1); a fix to a technology's handling applies to all its projects at once (R6).

### What it costs

- The recipe layer is itself software: recognition logic, lifecycle defaults, and procedures all age — and **a stale recipe is worse than none, because it is followed faithfully.**
- Recipes have a granularity problem in both directions (too coarse to fit, too fine and they're copies) that needs judgement to keep right.
- A recipe can lag the platform it targets; an admission by an outdated recipe produces exactly the bespoke drift this record exists to prevent.

### Watch

- A recipe is documentation, and documentation that contradicts reality is a defect: a recipe that no longer works is fixed, not tolerated as a draft.
- When a technology is eventually removed, executing the checklist and closing it is this record's removability claim tested for real.
- The boundary between "new technology" (this record) and "new version of an existing one" (dependency policy, [020](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/020-dependencies-stay-current-by-default/index.md>)) is a judgement the recipes should make explicit as they grow.

> [!NOTE]
>
> **Why write removal wiring at admission?**
>
> Because removal knowledge decays fastest: it's exercised once, at the worst possible moment, by whoever least knows the slice. Capturing the checklist while the wiring is fresh costs minutes; reconstructing it during a removal — from commits made by people who've moved on — is the cost this rule refuses to pay twice (R5).

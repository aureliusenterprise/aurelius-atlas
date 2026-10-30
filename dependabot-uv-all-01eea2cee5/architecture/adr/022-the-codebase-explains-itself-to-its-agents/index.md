# 022\. The codebase explains itself to the agents that change it

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Automated agents routinely author changes here, so every project directory carries a short instruction file written for machine readers. Nearest file wins; an instruction that drifts from the code is a defect.

## Decision

**Every project directory and technology grouping carries a colocated instruction file for machine readers.** Each file names:

- how to build, test, and run what lives here;
- which local conventions apply;
- what the surrounding wiring is;
- what to update elsewhere when something here changes.

**The rule is nearest-first.** Whoever — or whatever — edits a file reads the instruction files from the workspace root down to that file's directory; the nearest wins on conflicts. Each file is small and scoped. **The root file holds only workspace-wide rules and no catalogue of projects** — a catalogue duplicates what the directory files say and is the first thing to drift. The root may hold a removal map ([002](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/002-modules-are-removable-slices/index.md>)): which slices are optional is a workspace-wide rule, not a project description.

The practice is held to the documentation standard ([003](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/003-every-project-documents-itself/index.md>)): an instruction that no longer matches reality is a defect fixed in the change that broke it, and human-facing documentation never cites the machine-facing files. **This is not a courtesy to tooling** — it is the mechanism that lets a team of people and agents share one codebase without a shared memory of its conventions.

## Context

The team is one small multi-disciplinary group; the repository is polyglot, deeply wired (tasks, pipeline steps, environment keys, and documentation reference each other), and designed for removal ([002](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/002-modules-are-removable-slices/index.md>)). Knowing how a change in one place affects another is the hardest knowledge to get hold of, and it lives in only two places: the documentation, which serves humans, and the memories of the people who have been here longest.

**Agents now make changes here routinely** — the commit history carries agent co-authorship trailers beside the bot-authored updates that have been routine for years — and they change how cheap it is to produce a change. An agent absorbs nothing by immersion: it has no memory between tasks, so it confidently makes a change that is correct locally but violates a wiring rule nobody told it about:

- updating a schema but not its registration;
- adding a dependency but not its license entry;
- running a suite in watch mode and hanging the pipeline.

New humans make the same mistakes at first; **an agent makes all of them, every time, until told.** And an agent follows a written rule exactly, every time, once it is written where the agent reads it.

The two audiences read differently.

- A person builds a mental model and benefits from narrative.
- An agent executes instructions and benefits from short, local, unambiguous rules placed where its work begins.

Keeping the layers separate — this record complements [003](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/003-every-project-documents-itself/index.md>), it does not repeat it — keeps both honest: neither layer can hide the other's drift. The safety net is unchanged: an agent-authored change passes the same gate as a human-authored one ([014](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)). The instruction layer exists so agents arrive with the right context, not so they can be trusted without evidence.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Correct work is possible from the repository alone.** A competent agent with no prior knowledge makes a correct change in any area; oral tradition is not a dependency. |
| **R2** | **Instructions are nearest-first and small.** Rules found by walking root → file; each short enough for working context; nearest wins. |
| **R3** | **Wiring obligations travel with the code they govern.** The obligation is written where the first change is made, not in a central list. |
| **R4** | **The two reader layers stay separate.** Human documentation never cites the machine files; each layer stands alone for its audience. |
| **R5** | **Instructions are held true like tests.** A contradiction is a defect; the repair lands in the same review as the break. |
| **R6** | **No privileged path for agents.** Same gate, review, and release rules; the instruction layer informs, it does not authorize. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| One central instruction document | R2: a central file grows until it exceeds the context it was meant to fit in. R3: conventions written far from their code are the ones that drift. R5 in practice: nobody editing one project reads, or can maintain, a document about all of them. |
| No instruction layer; rely on the gate | Keeps R6, passes nothing else: the gate catches violations it knows about, and the wiring obligations (R3) are precisely what no check encodes — a missing registration, a stale removal checklist. Every miss it lets through costs a full human review — the scarcest capacity the small team has. |
| Instructions embedded in human documentation | R4, then R2: files written for both readers satisfy neither — the agent's rules drown in narrative, the human's narrative accretes machine boilerplate — and one layer's drift hides inside the other. |
| Per-tool configuration only | R1: the knowledge is bound to one vendor's tool and one developer's machine. R5: the rules live outside the repository, where no change can update them. |
| Do nothing (agents read the code alone) | R1 for anything the code doesn't literally show — wiring, removal, cross-file obligations. R3 entirely: locally-correct, globally-wrong changes at machine speed, and the review burden lands on the few humans who remember the wiring. |

## Tradeoffs

### What it buys

- Knowledge of the wiring — the hardest knowledge to hold — becomes a repository asset instead of a memory in someone's head (R1, R3).
- Agents and newcomers start every task with the same local truth (R2).
- Keeping instructions current surfaces documentation drift early: a broken instruction is noticed the next time anything works in that directory (R5).
- Human documentation stays clean of machine scaffolding (R4).

### What it costs

- Every directory carries a maintenance artifact: the instruction files age, and **a stale one actively misleads an agent that follows it faithfully.**
- The nearest-first rule needs judgement about what belongs at which level; a rule written at the wrong level is ignored or over-applied.
- No gate can check an instruction's truth, so R5 rests on review discipline — [003](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/003-every-project-documents-itself/index.md>)'s obligation, now with a second, less forgiving reader.

### Watch

- The recipes for admitting new technologies ([021](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/021-a-new-technology-joins-by-recipe/index.md>)) naturally live in this layer: keep the two practices consistent as they grow.
- If agents author changes at materially higher volume than people, the review burden shifts to the gate, and the standing obligation becomes encoding more wiring rules as checks rather than prose.
- The root file stays small by design: growth there signals a rule that belongs one level down — a review judgement, not an automation.

> [!NOTE]
>
> **Why not one file at the root — isn't that simpler?**
>
> It fails at scale in both directions. It grows past the context window it exists to fit (R2), and conventions written far from their code are the ones that drift (R3, R5). Nearest-first keeps each rule short, local, and in the change's line of sight.

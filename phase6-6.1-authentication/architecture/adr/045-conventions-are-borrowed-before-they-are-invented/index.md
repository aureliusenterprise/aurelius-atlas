# 045\. Conventions are borrowed before they are invented

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Aurelius Enterprise

Every convention is borrowed along a three-rung ladder — the framework's, then the community's, then a local rule — and each rung must be shown empty before the next. In-house dialects are the most expensive knowledge a codebase can hold.

## Decision

**A ladder of three rungs.** Every convention the organisation could write is borrowed first:

1. **The framework's conventions.** When a technology slot is filled — a web framework, a frontend framework, a validation library — the default is the mainstream option whose conventions do the most work: the framework decides where code goes, how it is wired, and what is valid, so the organisation writes rules only where the framework is silent.
2. **The community's conventions.** Where the framework is silent, adopt the settled habits of its ecosystem — naming, test layout, commit titles — rather than inventing.
3. **A local rule.** Invention is permitted only where no framework or community convention covers the gap, and it names the empty rung it stands on.

**New stacks ask the ladder first.** A technology joins by recipe ([021](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/021-a-new-technology-joins-by-recipe/index.md>)), and the recipe's first question is "which existing convention already covers this?", not "what shall we invent?". An organisation this size does not write a framework, or a dialect, to make a choice it can borrow.

**Borrowing is load-bearing, not decorative.** Framework majors are planned events, not routine updates ([020](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/020-dependencies-stay-current-by-default/index.md>)), and a framework's defaults are adopted through the declared channel rather than trusted silently ([018](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)).

## Context

The repository spans several stacks maintained by one small, multi-disciplinary team, and it is changed routinely by automated agents as well as by people ([022](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)).

- **Invented rules cost attention forever.** Every convention the organisation invents must be written down, taught to every new joiner, restated in the machine-facing instructions, checked in review, and re-learned by every agent session — forever, and per stack. Every borrowed convention is known by every new joiner who has worked in that ecosystem, and is the shape an assistant produces when nobody tells it otherwise.
- **The failure has a known shape.** A feature-first choice leaves the framework's job half-done, the team finishes it privately — a directory layout, a wiring style, a settings story — and maintains a small framework nobody outside can read. That private dialect is the most expensive kind of knowledge in a codebase: it exists only in the heads of the people who wrote it, and it is exactly the knowledge an agent cannot pick up on its own.
- **The same reasoning applies below the framework level.** A framework cannot settle every habit — commit titles, test naming and placement — and those gaps are where teams grow a house style. But most gaps already have a settled community answer, and a borrowed community convention carries the same assets as a borrowed framework convention.
- **The record must outlive the brands.** Frameworks and libraries change while the business reasoning does not, so this record states the *preference* that governs how conventions are acquired — not which framework fills which slot today.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Structure arrives borrowed.** The framework, then the community, supply the default answers for layout, wiring, validation, and everyday habits, so the written rule set stays small and covers only genuine local decisions. |
| **R2** | **Strangers read the code.** A competent outsider — joiner, reviewer, or assistant — who knows the stack reads the code without learning a private dialect; understanding is a hiring and onboarding asset ([003](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/003-every-project-documents-itself/index.md>)). |
| **R3** | **The convention is load-bearing on purpose.** Upgrades are planned, defaults are validated through the declared channel, and the convention is not quietly worked around. |
| **R4** | **The choice stays replaceable.** The preference is about properties, not brands; replacing a framework is a planned migration under [020](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/020-dependencies-stay-current-by-default/index.md>), not a decision reversal. |
| **R5** | **New stacks join through the same gate.** A technology that genuinely needs new ground enters by recipe ([021](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/021-a-new-technology-joins-by-recipe/index.md>)) with its conventions documented beside it. |
| **R6** | **Invention is the last resort.** A local convention is permitted only where no framework or community convention covers the gap; an invented rule that could have been borrowed is a defect of the same kind as a private dialect. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Feature-first selection | Choose the most capable framework. R1: capability-first choices are typically the least opinionated, and the unopinionated space is filled by an invented in-house dialect — the cost R1 exists to avoid. |
| In-house framework | Fails R2 by design: the dialect is private. R3: the team that builds a framework also has to operate, document, and staff it, which a small team pays for twice. |
| Private house style | Keep the frameworks, invent the open habits. R6 where a borrowed answer exists; R2 where the invented answer diverges from what joiners and assistants arrive knowing. A style guide is still a rule re-learned by every session. |
| Maximal minimalism | One language, one framework, nothing new ([021](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/021-a-new-technology-joins-by-recipe/index.md>) rejects this). R1 and R2 for the stacks it keeps; R5: it freezes the stack rather than expressing a preference about how new parts join. |
| No stated preference | Decide each slot ad hoc. R4: the absence of a rule is itself decided differently every time. R1: ad hoc selection drifts toward the familiar-but-thin option, and invented conventions return. |
| Do nothing | Keep the stack without recording why. R3: an unrecorded preference is argued again at every upgrade, and the first "just this once" exception starts the drift back to the private dialect. |

## Tradeoffs

### What it buys

- The written rule set stays small because the framework and its community carry the structure and the habits (R1, R6).
- Onboarding and assistant-authored changes start from the stack's conventions instead of a local dialect (R2), which lightens the instruction layer ([022](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)).
- Review spends attention on meaning because form is typical of the stack.
- The preference is brand-independent, so it survives every migration (R4).

### What it costs

- Mainstream conventions are not always the best conventions: the team inherits decisions it did not make, and escaping one — a framework fighting a requirement — costs more than never adopting it.
- Community conventions are softer than framework ones: they shift, and two communities can disagree, so R6's "no convention covers this" needs judgement at the edges — and a settled habit the team dislikes must be swallowed or consciously opted out of, not silently diverged from.
- The commitment is real: planned majors ([020](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/020-dependencies-stay-current-by-default/index.md>)) and declared-channel settings ([018](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) are obligations, not decorations.
- "Mainstream" narrows the field in a way that must be re-examined when a genuinely better convention matures.

### Watch

- Which framework fills which slot today is an implementation note and deliberately absent from this record — it belongs in the project documentation that describes each stack ([003](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/003-every-project-documents-itself/index.md>)).
- The enforcement point is the recipe review that every new technology passes through ([021](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/021-a-new-technology-joins-by-recipe/index.md>)).

> [!NOTE]
>
> **Why is a private style guide a defect?**
>
> Because every rule in it is paid for forever: written down, taught, restated to agents, and checked in review, while a borrowed rule arrives free with the ecosystem. A house style guide is a dialect with documentation — and a dialect is precisely what joiners and agents cannot pick up on their own (R2, R6).

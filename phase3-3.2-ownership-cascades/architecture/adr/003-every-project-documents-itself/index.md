# 003\. Every project documents itself

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Knowledge lives beside the thing it describes: every project carries its own documentation, and the repository maintains no hand-edited central catalogue. The tree is the index.

## Decision

**Documentation travels with its subject.** Every project carries its own — what it is, how to run it, the rules that govern it — and the repository maintains no hand-edited central catalogue of projects or capabilities.

**The repository tree is the index:** to find what exists, read the tree; to learn a part, read what sits beside it. Derived artifacts — generated API reference, navigation derived from the tree — are not catalogues in the sense this rule forbids, because they cannot disagree with the code.

> [!NOTE]
>
> **Isn't the site's nav list a central catalogue?**
>
> It is the one hand-edited list this rule tolerates. It enumerates documents rather than describing projects, and the build reports every entry that no longer resolves and every document the list omits — drift is loud at build time, not quiet at read time. That is the property R2 asks of everything else.

## Context

People constantly need to learn parts they did not build: what a part is for, how to run it, what breaks if it is removed. The team is small and multi-disciplinary, and the person who changes a project today is often not the person who needs to understand it next — so what the system does cannot live in anyone's head.

Where documentation lives decides how fast it decays:

- **Central knowledge** changes only when someone remembers to update it, drifts from the code, and readers learn to distrust it.
- **Knowledge beside the code** changes in the same review, is reviewed with it, and is deleted with it.

The decision is where knowledge about a part belongs, and what must be updated when that part changes.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Knowledge travels with the part.** Project and documentation change in the same review. |
| **R2** | **Drift is structurally impossible.** No hand-edited central artifact quietly goes stale. |
| **R3** | **Local discovery is enough.** Learn a part without leaving it. |
| **R4** | **Removal takes the knowledge with it.** Deleting a project deletes its documentation. |
| **R5** | **Cheap to keep true.** Honouring the rule costs nothing beyond the change already being made. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| A curated catalogue of every project | R2: a hand-edited page is updated when someone remembers — precisely how catalogues come to be disbelieved. R1: every change is a two-place edit in two reviews. R3: answering about a part means leaving it. |
| The project wiki | R1: edited by whoever remembers, reviewed apart from the change, so it drifts. R3: the answer lives elsewhere. R4: deleting a project leaves its page standing. |
| No rule (knowledge in people and history) | R3 by default: every question about an unfamiliar part becomes a question to a person. R1: nothing connects what changed to any written account. |
| Documentation generated from code only | R2 holds trivially — derived text cannot drift. R1 fails: code states what a project does, not why it is shaped that way; the reasoning must be written by a person, somewhere. |

## Tradeoffs

### What it buys

- Documentation is reviewed with the change it describes — current exactly where people work (R1).
- Drift is not discouraged but impossible: there is nothing central to forget (R2).
- Removal leaves no stale text (R4) — what makes whole-slice removal trustworthy ([002](<https://aureliusenterprise.github.io/phase3-3.2-ownership-cascades/architecture/adr/002-modules-are-removable-slices/index.md>)).

### What it costs

- No single page answers "what does the system contain?" — discovery means browsing the tree, slower for a newcomer who doesn't yet know what to look for.
- The shape of a project's documentation is a convention: keeping twenty documents consistent without an enforcing tool takes deliberate effort.

### Watch

- "Documents itself" needs a shared shape — what every project's documentation must contain — or the rule degrades into twenty unrelated files. Directory-level recipes for adding new projects carry that shape; keeping them current is ongoing work.
- The removal rule in [002](<https://aureliusenterprise.github.io/phase3-3.2-ownership-cascades/architecture/adr/002-modules-are-removable-slices/index.md>) depends on this record: a capability is fully removable only when its documentation is part of the slice.

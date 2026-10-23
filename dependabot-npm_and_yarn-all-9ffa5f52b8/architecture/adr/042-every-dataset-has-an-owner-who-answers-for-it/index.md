# 042\. Every dataset has an owner who answers for it

- **Status:** Proposed
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Every dataset the system keeps has an owner — a named role that answers for its shape, lifetime, and quality. A dataset may be declared shared, but sharing is itself the ownership answer, with a named custodian.

## Decision

**Every dataset has a name beside it.** Every dataset the system keeps — a table, an index, a store of operational signals — has an owner: a named role that answers for its shape, its lifetime, and its quality, and whose approval a change to those needs. **A dataset may be declared shared, but sharing is itself the ownership answer**, recorded with a named custodian — not the absence of one.

Until this record is accepted, a dataset with more than one writer has no answer at all, and disagreements about it are settled by whoever edits first.

## Context

The system keeps data in places with different lives: business rows in stores, operational signals in their own stores. Each raises the same quiet question — **who answers for this?** — and today the answer is nowhere written.

The question stopped being theoretical the moment one store grew a second hand. The record's founding example — the database the API writes and the event sink also writes — travelled with the streaming slice ([050](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)), but the shape it exposed is permanent: **one store, several hands, each shaped by a different part's needs.** A change to what a row means is a change to what the other hand stores, and neither part's tests can see the other's assumption.

> [!NOTE]
>
> **The founding example, and why the shape outlives it**
>
> The example — one database written by both an API and an event sink — arrived with the streaming slice and left with it ([050](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)). The lesson did not: any store with two writers has it. The catalogue's own audit writer and entity store meet the same shape when increment 3.5 lands, so the ownership question the record answers is not a leftover of the slice.

Two records meet at this gap and stop short of it:

- The migration record ([023](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/023-storage-schema-changes-by-recorded-migration/index.md>)) decides how a schema changes; **it cannot decide who says yes.**
- The shared-concept record ([004](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/004-one-shared-domain-model/index.md>)) decides a concept has one canonical definition; it does not decide who answers when two parts want the definition to bend.

The softer costs are real. A person asking "can we trust this number?" has no one to ask. A dataset nobody owns is a dataset nobody notices decaying, and its lifetime question ([025](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/025-data-has-a-stated-lifetime/index.md>)) has no one to answer it in practice. When a dataset is retired, nobody can say what still reads it.

**The force is not team size** — even one team hands over: new joiners, agents working from the codebase, future reviewers all ask "who cares about this table?" and today the codebase does not say.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Every dataset has a name beside it.** A named role answers for each; the list of datasets and owners stays small enough to stay true. |
| **R2** | **Sharing is a stated answer.** Several writers means declared shared, with a named custodian who arbitrates shape. "Several writers, no answer" is not permitted. |
| **R3** | **The owner's say is defined.** Shape, lifetime, or meaning changes require the owner's approval, named in the change — not consulted by folklore. |
| **R4** | **Ownership survives people.** The owner is a role, not a person's memory; when the person changes, the answer does not. |
| **R5** | **The answer is findable.** "Who owns this?" answered beside the dataset or in one short list, not by asking around. |
| **R6** | **Cheap to keep true.** A new dataset arrives with its owner named in the change that creates it — one line, not a ceremony. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Ownership by writer (status quo) | R2 the moment a second writer appears — which has already happened. R3: two writers means two answers, and the one that wins is whoever ships first. |
| Ownership by the whole team | R1 in practice: everyone cares, so no one answers — a question about the data has no address, and R3's approval is a meeting instead of a decision. |
| A data governance board | R6 at this scale: a board for a handful of datasets is ceremony the first urgent change routes around, and a routed-around process is worse than none. |
| Ownership by the schema's source of truth | R2 directly: the shared store is precisely the case where two models meet. R5: the answer is a deduction from code, not a stated fact. |
| Do nothing | Free today. R1: the question goes unasked. Every later record that needs an owner — lifetime, quality, lineage, compliance — inherits the silence. |

## Tradeoffs

### What it buys

- Questions about data have an address (R1, R5).
- The shared store's multi-writer problem gets an arbiter instead of a race (R2).
- The lifetime and quality questions finally have someone to answer them — [025](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/025-data-has-a-stated-lifetime/index.md>) assumes this record supplies.
- A new joiner or agent learns who cares about a table without asking (R4, R5).

### What it costs

- Ownership lines are upkeep: **a dataset whose owner left is a lie waiting to be read**, so R4 needs a real hand-over habit.
- Naming an owner invites ownership to expand into style review and veto over everything; R3 must bound it to shape, lifetime, and meaning.
- Declaring a dataset shared with a custodian still concentrates arbitration in one role — exercised visibly, or it decays into the status quo with extra paperwork.

### Watch

- The mechanism — where the dataset-and-owner list lives, how a change proves the owner's approval — **must be named at acceptance, not deferred.**
- The division of labour: [023](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/023-storage-schema-changes-by-recorded-migration/index.md>) decides how a schema changes and this record decides who says yes; [004](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/004-one-shared-domain-model/index.md>) decides what a concept means and this record supplies the role that answers when meanings are contested; [025](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-9ffa5f52b8/architecture/adr/025-data-has-a-stated-lifetime/index.md>) needs an owner per kind of data to state its numbers, and this record is where that owner comes from.
- The placeholder pages on data-governance roles and the data dictionary remain headings until acceptance; the lineage and compliance questions under the same section lean on this record's substrate and should not be framed before it.

> [!NOTE]
>
> **Why is 'owned by the team' not good enough?**
>
> Because it dissolves exactly when a decision is needed (R1, R3). "The team cares" has no address to send a shape change to, no name to put on an approval, and no one who notices decay. The record allows shared datasets (R2) — what it forbids is a sharing answer with no custodian attached.

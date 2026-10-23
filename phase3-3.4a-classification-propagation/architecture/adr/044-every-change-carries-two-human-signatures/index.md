# 044\. Every change carries two human signatures

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Aurelius Enterprise

Every change that merges carries two human signatures — the task owner and one reviewer — enforced by a mechanism that refuses the merge. An assistant may produce, test, and review a change; it signs nothing.

## Decision

**Two signatures, both human.** Every change that merges into the mainline carries the **task owner** — the person who asked for the change, who can explain it, and who states how far they verified it locally — and **one reviewer**, a second person who confirms independent understanding.

**A tool signs nothing.** An automated assistant may produce, test, and review a change, but accountability is carried by the team and cannot be offloaded to a tool.

**The rule has an enforcement point.** A mechanism refuses the merge without the second approval; the rule is not held by custom.

## Context

The repository is changed routinely by automated agents as well as by people, and the cost of producing a plausible diff has fallen sharply. The obligation attached to a change has not: the team must be able to own what it ships, and ownership requires understanding.

- **Understanding is no longer a side effect.** Before fast generation, the author's understanding came free with writing the code by hand. Now a change can arrive working, gated, and reviewed by machines while nobody on the team fully understands it. The failure is quiet — it surfaces at the next incident, the next change to the same area, the next handover — and the delay is what makes it debt rather than a defect.
- **The oldest review rule needs teeth.** The contributor guide has always required a second pair of eyes. That rule was written for a slower generator; what changes when code is produced quickly is how load-bearing it becomes, and a rule held only by custom is the first thing a fast queue erodes.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **A human answers for every change.** A named person can explain each merged change and carries it; "the assistant wrote it" is not an answer to "who owns this?". |
| **R2** | **Understanding is independent.** At least one person besides the task owner reads the change for understanding before it merges; self-approval is not approval. |
| **R3** | **Verification is stated, not assumed.** The task owner records how far they verified locally, so a reviewer knows whether "it works" means lint passed or the real system ran. |
| **R4** | **The rule has an enforcement point.** A mechanism refuses the merge without the second signature — not a convention that erodes when delivery is late. |
| **R5** | **Cheap enough to keep.** Two signatures on a typical change is minutes, not a ceremony; the rule must not push people to route around it. |
| **R6** | **Knowledge moves with review.** The reviewer is chosen at least partly for who should learn the area, so review doubles as knowledge spread. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| One signature (the status quo) | R2: the gate checks form and behavior, not whether anyone understands; R6: knowledge concentrates in whoever prompted the change. |
| Machine review is enough | R1 and R2: a machine verdict is evidence, not accountability — the organisation still needs a person who can explain the change six months from now. |
| Committee approval for agent changes | R5, and it contradicts the no-privileged-path rule ([022](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)): risk follows blast radius, not the typist's identity, and a special lane trains the team to hide assistant involvement. |
| Custom only | R4: the first urgent merge that skips review establishes the exception, and at generated volume the exceptions become the rule silently. |
| Do nothing | R1, the first time a change breaks and nobody on the team can explain it. |

## Tradeoffs

### What it buys

- Every merged change has a human who can explain it (R1) and a second human who is starting to (R2, R6).
- The verification statement makes the strength of "it works" visible at review time (R3).
- The merge mechanism turns the oldest review rule in the guide into an enforcement point (R4) — what [017](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/017-shared-concepts-change-only-compatibly/index.md>) asks of review-only conventions.

### What it costs

- Two humans per change is the scarcest budget in a small team, and generation volume can make the second signature the bottleneck — the pressure is to approve quickly, which R6 mitigates only if reviewer selection stays deliberate.
- Declaring the task owner adds one line of ceremony to every pull request.
- The merge mechanism can be overridden by repository administrators, so it needs the same habit as the gate (the shared set of checks every change must pass, [014](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)).

### Watch

- The mechanism that makes R4 true lives in the hosting platform's merge settings — an implementation detail of where the rule is enforced, not part of the decision. The pull request template carries the two signatures and the verification statement.
- Assistant review is governed separately ([043](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/043-ai-assisted-review-informs-the-signatures-it-does-not-replace-them/index.md>)); the no-privileged-path rule is this record's neighbour, not its source ([022](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)); what the reviewer may rely on the gate for is decided by the blocking rule ([015](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)).

> [!NOTE]
>
> **The owner understands the change — why is a second human needed?**
>
> The owner's understanding is exactly what generation makes unreliable: a change can arrive working and gated while nobody, including the owner, fully grasps it (R2). The second reader is the only independent check that understanding exists at all — and choosing that reader deliberately is how knowledge spreads instead of concentrating (R6).

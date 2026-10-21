# 043\. AI-assisted review informs the two signatures; it does not replace them

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Aurelius Enterprise

Automated review is a welcome first pass on any change. Its findings follow the ordinary blocking rule; its approval is never one of the two human signatures, and dismissing a machine finding is a human act, recorded as one.

## Decision

**The assistant reads first; the humans sign.** Automated review — an assistant reading the diff and leaving findings — is a permitted and welcome first pass on any change, human- or agent-authored.

Its findings obey the ordinary rule: those about the change itself block when the gate (the shared set of checks every change must pass, [014](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)) enforces them, and those about the state of the world are advisory evidence for the cadence review ([015](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)).

**An automated review comment is never an approval:** the two human signatures stand ([044](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)), and dismissing a machine finding is a human act, recorded as one.

## Context

A small team has little review time, and fast generation multiplies the volume of diff arriving at it.

The team already uses assistants to read diffs — the commit history carries the residue of applied review feedback — **but an unstated practice drifts in the direction of least effort:** first toward treating a machine's approval as the second signature, then toward dismissing its findings without reading them, then toward skipping the human review the machine seemed to make unnecessary.

Each drift has a known failure:

- **A machine cannot be accountable for a merged change** ([044](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)), so an approval that is not a human's leaves R1 unanswered.
- **Machine findings include plausible mistakes**, and a finding dismissed unread is a defect adopted with confidence.
- **Treating every machine finding as blocking** would import the noise of the whole ecosystem into the merge gate — the exact failure the blocking rule exists to prevent ([015](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)) — and would train the team to bypass the review as they bypass a noisy gate.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The signatures stay human.** Automated review may inform both signatures, satisfy neither; no workflow accepts a bot approval as the second pair of eyes. |
| **R2** | **Machine findings follow the blocking rule.** A finding blocks only when the defined gate enforces it; a reviewer's judgement of a machine comment never changes what blocks. |
| **R3** | **Dismissal is a human act.** Every rejected machine finding is dismissed by a named person, visible in the review — a wrong machine verdict cannot silently become a merged defect. |
| **R4** | **Volume does not lower the bar.** The practice must hold when review volume is high; a practice that only works with a short queue is the first thing skipped under pressure. |
| **R5** | **Cheap to keep true.** No new roles, queues, or dashboards; the practice rides the review surface the team already uses. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| No automated review | Passes R1 trivially, but fails the reason the practice exists: at generated volume, human review without a machine first pass becomes the bottleneck that squeezes understanding out of the second signature. |
| Machine approval as the second signature | Fails R1: a bot cannot explain the change in six months, cannot carry it in an incident, cannot be the accountable party — the same point [042](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/042-every-dataset-has-an-owner-who-answers-for-it/index.md>) makes about ownership. |
| Machine findings always block | R2 and R4: machine review produces confident nonsense at a steady rate, and a gate that must be argued with is a gate that gets bypassed — the failure named in [015](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>). |
| Machine findings invisible (off the review) | Findings go to a side channel. R3: dismissals happen off the record. R5: a second surface is a second thing to maintain, then ignore. |
| Do nothing (status quo, unstated) | The practice continues without a boundary. Fails R1 gradually: each relaxation is individually reasonable, and together they replace the second signature. |

## Tradeoffs

### What it buys

- The team keeps the capacity gain of a machine first pass without letting it redefine accountability (R1).
- Machine findings arrive where humans already read, at no new ceremony (R5).
- The dismissal rule turns each wrong machine verdict into visible evidence about the tool, rather than an invisible defect (R3).

### What it costs

- Machine review consumes human attention to triage its findings, and at high false-positive rates the tax can exceed the saving — **the response is to tune or drop the reviewer, never to relax R3.**
- The rule depends on reviewers actually reading machine comments: the same review-discipline dependency the instruction layer carries ([022](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)).

### Watch

- R1's force rests on the merge mechanism that enforces the two signatures ([044](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)); R3's dismissal habit on review discipline ([022](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)).
- Whether machine findings should ever be promoted to blocking is a decision under [015](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>), not this record.

> [!NOTE]
>
> **If the bot finds the bug, why can't its approval count?**
>
> Because an approval is an assumption of accountability, and a bot can't carry one: it cannot explain the change in six months, own it in an incident, or answer for a dataset it blessed (R1, [042](<https://aureliusenterprise.github.io/phase2-2.1c-entity-validation/architecture/adr/042-every-dataset-has-an-owner-who-answers-for-it/index.md>)). The bot's finding is welcome — the human who reads it and signs is the mechanism.

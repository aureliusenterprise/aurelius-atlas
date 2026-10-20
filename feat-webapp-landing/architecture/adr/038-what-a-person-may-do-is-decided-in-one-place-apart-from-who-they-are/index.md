# 038\. What a person may do is decided in one place, apart from who they are

- **Status:** Proposed
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Acceptance trigger (swept 2026-10-19): increment 6.2 makes the authorizer's policy the one permission answer on every endpoint; accepted in that pull request. Until then the record's stated condition stands: every admitted person may do everything.

The answer to "what is this person allowed to do?" lives in one named place, apart from the answer to "who is this person?". Surfaces ask and act; they do not invent permission rules in code.

## Decision

**One authorizer, consulted not embedded.** The answer to "what is this person allowed to do?" is held and enforced in one named place, deliberately apart from the answer to "who is this person?" ([007](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/007-one-shared-identity-provider/index.md>)). Surfaces ask that place and act on the answer; **they do not invent their own rules in code.**

Until this record is accepted, every authenticated person can do everything on every surface, and that is **a stated condition, not a security property.**

## Context

The system already knows who a person is: one identity provider admits people and every surface verifies what it issues, so no surface keeps its own account list. That answers admission; it does not answer permission. Today, once a person is admitted anywhere, they are admitted everywhere: the screens, the APIs behind them, and the operational tooling act on the verified identity and nothing else.

For the system as it stands — an arrangement being validated, with examples that demonstrate the shape — that is workable, and pretending otherwise would be false. **But the system is meant to be deployed into environments that keep business data**, and there "why could this person change that?" has to have an answer.

**If nobody decides, the arrangement that exists is accidental:** the first feature that needs a restriction grows a private check, the second grows a different one, and permission — the one security property auditors ask about most directly — becomes folklore scattered through surface code.

The forces are the same ones that settled identity: several surfaces, one truth, revocation that takes effect everywhere at once. Permission inherits them and adds one: **a rule inside a surface can only change by releasing that surface, while the business reason for the rule changes on its own schedule.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One answer about permission.** One authoritative statement of what each person or role may do; no private surface rules. |
| **R2** | **Revocation is one action.** Withdrawing an allowance withdraws it at every surface, without releasing those surfaces. |
| **R3** | **Surfaces ask, then act.** Enforcement consults the decided answer; the security-critical judgement is written, reviewed, and patched once. |
| **R4** | **The answer is auditable.** "Who could do X, and when?" answered from the arrangement's records, not a code survey. |
| **R5** | **Permission runs where validation runs.** The restricted path is live on one machine and in the pipeline, exercised routinely. |
| **R6** | **Cheap to keep true.** A new surface or action joins the decided arrangement; the default is the shared answer, not a private check. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Permission inside each surface | R1: the truth is wherever the last check was written. R2: withdrawal is a release per surface. R4: the audit is a code survey. |
| Permission at the network edge only | R3 for anything the edge can't see — an event consumed directly, a call between parts. R4: the edge knows what was attempted, not what the business action meant. |
| Role names baked into surface code | Familiar and quick; R2 and R3: the meaning of a role is distributed across every release, and changing what a role may do is a code change everywhere at once. |
| Defer permission entirely (status quo) | Honest for a system with no business data yet. R1: the question is unowned. R6: the first urgent restriction is a bespoke check under time pressure — the arrangement every later one copies. |
| Do nothing, hope the deployment adds it | R5: a permission path that exists only in a deployment is a path no earlier run has exercised. |

## Tradeoffs

### What it buys

- Permission questions have one address (R1, R4); withdrawal is one act, not a release checklist (R2).
- Surfaces stay thin, as identity made them thin.
- The restricted path is exercised where every other security path is exercised (R5).

### What it costs

- One more decision point in the request path, with its own failure mode to design for: **what a surface does when the permission answer is unreachable is a question this record must eventually answer.**
- The arrangement is one more part to run locally and in the pipeline.
- Naming roles is a business act that is wrong sometimes, so the arrangement must make being wrong cheap to fix.

### Watch

- The identity arrangement it sits beside is accepted ([007](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/007-one-shared-identity-provider/index.md>)) and stays re-opened-free: admission and permission remain separate answers even if one product holds both. The access-management placeholder page stays a heading until this record is accepted and written from its answer.
- Machine identity for part-to-part calls belongs to [013](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>), not here.
- On acceptance, **the named mechanism must exist in the spine (the parts that always stay, [002](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/002-modules-are-removable-slices/index.md>)) before the status changes.**

> [!NOTE]
>
> **What if the authorizer is unreachable — fail open or closed?**
>
> Failing open would make availability the tiebreaker on every security question; this record's posture ([037](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/037-the-system-itself-promises-nothing-about-staying-up/index.md>)) refuses promises it can't keep in either direction. The posture it takes is the obligation: the behaviour is a named design decision at the seam, not an accident of timeout handling.

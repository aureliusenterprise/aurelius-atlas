# 041\. A failure of the running system has an owner and a rehearsed path

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Accepted 2026-10-19: the owner of the response is the maintainers team; the path from noticing to closing, the rehearsed steps, and the incident record live in [Operations Ownership](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/contributor-guide/operations-ownership/index.md>). R4 holds today — the responder reads the system's own picture in the dev observability stack (ADRs 016, 034). Named gap: the detection half is the alerting arrangement of [040](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/040-the-system-raises-its-hand-when-it-is-broken/index.md>), scheduled with increment 6.4; the first rehearsal is scheduled.

When the running system fails, a named owner follows a written, rehearsed path. "Whoever notices" is not an owner, and an unwalked path is a paragraph.

## Decision

**A named owner, a written path, a rehearsal behind both.** When the running system fails, the response follows a named path with a named owner: someone is answerable for deciding, someone for acting, and the steps — who is told, what is tried, when it escalates, what is written down afterwards — are written and rehearsed rather than improvised by whoever is nearest.

Before this record, the system had no incident path at all, and the owner of a failure became whoever happened to notice it — a default, not a decision.

## Context

The system is built to be handed over: the records explain the decisions, the examples teach the shape, the development arrangement runs the whole thing on one machine. **A failure response is the same kind of asset.** When something breaks in an environment that matters, the cost of the failure is dominated by the hours around it — who was told, who decided, what was tried in what order, what was learned afterwards — and those hours are cheap only when the path was walked before.

The organisation already conceded this principle once, for credentials: secret handling has a named owner and a rehearsed path, because a lost key at midnight is not the moment to invent a process ([028](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)). The running system has no equivalent. Today's implicit path — whoever notices acts, whoever acts is answerable, the lessons leave with the person who learned them — **has a name in every post-incident review ever written.**

Two properties of this system sharpen the question:

- **The boundary** ([016](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/016-the-system-observes-itself-internally/index.md>)) puts the evidence for any investigation inside the system, so the responder must read the system's own picture — an incident path that assumes a vendor's support line would be a fiction here.
- **The availability posture** ([037](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/037-the-system-itself-promises-nothing-about-staying-up/index.md>)) says the system prevents nothing on its own: failures happen, and the honest answer to "what then?" is the path this record decides. The detection half — how anyone learns something is wrong — is owned by [040](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/040-the-system-raises-its-hand-when-it-is-broken/index.md>); **this record starts where that one ends.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **An owner exists before the incident.** One named role answers for deciding, escalating, closing. "Whoever is available" is the absence of an owner, not a kind of one. |
| **R2** | **The path is written.** First signal to all-clear: who is told, in what order, what may be tried without asking, when it escalates, who says it is over. |
| **R3** | **The path is rehearsed.** A path nobody has walked is a paragraph; practising it is on the schedule the rehearsal decays at, at worst. |
| **R4** | **The evidence is reachable by the responder.** The responder reads the system's own picture without provisioning anything the boundary forbids. |
| **R5** | **Every incident leaves a record.** What happened, what was done, what changes — where a future responder, or the next audit, can read it. |
| **R6** | **Learning closes the loop.** A lesson that should become a rule or trigger becomes one — into alerting, recovery, or a new record — rather than resting in a file. |
| **R7** | **Cheap enough to survive.** The path fits one small organisation: rehearsing is hours per year, not a department. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Whoever notices owns it (status quo) | R1 by definition; R2: the path is invented at the worst moment; R5: the record of the incident is the chat log of whoever was paged. |
| A formal incident-management process, imported whole | ITIL-scale roles, severity matrices, war rooms. R7 at this scale: a process sized for a department goes unused by a team, and an unused process teaches the team to ignore process. |
| Ad-hoc escalation by seniority | Everyone knows who to call. R1: the owner is a person, not a role, and people leave. R3: a path carried in heads is unrehearsed by definition. |
| Defer until the first real incident | R3 outright: the first walk of an unrehearsed path is the incident itself, paid for by the people affected. R6: the lessons of that first incident are gathered by the exhausted people who lived it, if at all. |
| Do nothing | Free today; every requirement failed by the same silence — the current state described as a choice. |

## Tradeoffs

### What it buys

- A failure has an address before it happens (R1).
- The hours around an incident shrink because the path is known and walked (R2, R3).
- The organisation accumulates a written memory of its own failures (R5), and each incident makes the arrangement better instead of just over (R6).

### What it costs

- Naming an owner makes that role a single point unless backup is named too — the same hazard the secret-handling record accepts and manages ([028](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)).
- Rehearsal is real time spent on a disaster hoped against.
- A written path invites mechanical following when the incident does not match it — the owner's judgement must be trusted to override.

### Watch

- This record leans on the alerting record ([040](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/040-the-system-raises-its-hand-when-it-is-broken/index.md>)) for the moment an incident begins — and that record is itself Proposed, so **today the system neither raises its hand nor answers when one is raised.**
- The recovery half of a severe incident — bringing the system back from a named snapshot — is owned by [026](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>); this record is the path that invokes it.
- The owner role named here and the secret-handling owner ([028](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)) may be the same role or must at least know each other — decided at acceptance of both.
- The numbers — rehearsal cadence, escalation times — belong to whoever accepts this record and must be named then, not deferred.

> [!NOTE]
>
> **Why rehearse when the owner is one small team?**
>
> Because the path's value is exactly its unexercised state: nobody on the team walks an incident path weekly, so the only moments of practice are the rehearsal and the incident (R3). An unpractised path decays at staff turnover — a step naming a tool or person that has moved on is a paragraph, not a path.

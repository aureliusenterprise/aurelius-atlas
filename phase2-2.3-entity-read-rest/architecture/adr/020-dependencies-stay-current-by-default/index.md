# 020\. Dependencies stay current by default; majors move by decision

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Routine dependency updates arrive by themselves, one dependency at a time, and are accepted only when the automated checks pass. Upgrading a framework the system is built on is planned work, decided by a person. A dependency runs old only by a recorded choice.

## Decision

**Being up to date is the default.** Every ecosystem the system consumes — packages, container images, workflow actions, tooling — is monitored on a schedule, and routine updates arrive as automatic, reviewable changes, one dependency at a time. Each one passes the gate (the shared set of checks every change must pass, run at commit time and in the pipeline ([014](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>))), so an update is accepted by test evidence, not by trust in the automation.

**Framework upgrades are the exception, handled deliberately.** Where an update crosses a major boundary of a framework the system is built on — an upgrade that is a project, not a bump — the update automation deliberately stays away from it, and the upgrade happens as planned work on a date the team chooses. Everything else, including major versions of ordinary libraries, flows through the automatic channel and is judged by the gate.

> [!NOTE]
>
> **Why not automate framework majors too?**
>
> Because the gate cannot judge them. The tests can stay green across a framework major while the upgrade is really a migration of how the system is written; merging on green tests alone ships a decision nobody made (R4).

## Context

The system stands on a large base of third-party code — packages in three ecosystems, container images, CI actions, the toolchain — and all of it moves whether the system acts or not. The question is who decides when the base moves, and how quickly. Two failure modes bracket the answers:

- **Updates accumulate.** The system ages several generations behind; every catch-up is a breaking change compounded with the next, and security fixes arrive only inside those expensive jumps.
- **We chase every update the day it appears.** Most updates fix nothing this system cares about, attention goes to churn, and real regressions deserve a human deciding whether the affected part is worth the risk this week.

The resolution separates the two kinds of movement **by cost, not by version number**:

- An update the gate can judge — build it, test it, see — is cheap to accept and cheap to revert, so it arrives automatically and often: small, single-purpose, reviewable, like any ordinary commit.
- An update the gate cannot judge — the tests pass, but the upgrade is a migration of how the system is written — is not a bump at all. Framework majors are this case, so the automation is pointed away from them, toward the movement the gate's judgement is the right instrument for.

This record is the input side of the delivery rule ([019](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)): a release is a consistent snapshot only if the base under it is known and recent, and releasing as one whole is what makes an accepted update reach users.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **No ecosystem left unwatched.** Every kind of third-party thing consumed is monitored. |
| **R2** | **No human initiative for routine updates.** They arrive as proposed changes on a cadence, one each. |
| **R3** | **Updates are judged like changes.** The same gate; breakage refused by evidence, not found in prod. |
| **R4** | **Framework majors are planned, not automatic.** Scheduled work with a decision in front of it. |
| **R5** | **Age is visible.** A held dependency is recorded as held, with a reason — a choice, not drift. |
| **R6** | **Security fixes are not gated by cadence.** They ride the same automatic channel as everything else. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Update by hand, when someone remembers | R2, R6: updates correlate with novelty, not need. R1: watching eight ecosystems by hand is a job nobody holds. This is the arrangement the record replaces. |
| Automate everything, majors included | R4: a framework major is a migration dressed as a bump — green tests ship a decision nobody made. R5: a policy of never holding anything records no choices at all. |
| Pin everything, review quarterly | R6: a vulnerability fix waits for the review. R3: a batched upgrade names ten suspects when it fails. |
| Update only known vulnerabilities | By the time a CVE is published, the system has run the flaw for the age of the version. R2, R6: updating only in response to published flaws puts the whole burden on emergencies. |
| Do nothing | R1, R2, R5, R6 by definition; R3 quietly — un-updated dependencies eventually demand the least reviewable change of all. |

## Tradeoffs

### What it buys

- The base is known-recent at every release — the input [019](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>) needs.
- A failure names one suspect: updates arrive one at a time (R3).
- Security fixes ride the default channel, not an emergency one (R6).
- Coverage is a configuration fact, not a habit (R1).

### What it costs

- Review volume: most updates fix nothing the system cares about, so the team's habit must be merging single-dependency changes that pass the gate, quickly.
- The line between "ordinary library" and "framework the system is built on" is a judgement maintained as the system grows; a wrong call fills the queue with migration pull requests, or automates one without anyone noticing.
- Holds must be recorded — a small discipline with no immediate payoff.

> [!WARNING]
>
> **The decay mode**
>
> This arrangement fails without any alarm: nothing breaks, updates just stop being merged. A proposal queue that sits unmerged decays into the batched-upgrade failure this record replaces. The fix is the habit: updates that pass the gate are routine work, not a backlog.

### Watch

- The automation's ignore list is the registry of holds, each entry with its reason (R5). A held dependency is a known liability with a shelf life: keep the reasons current, and look here first in any operational review.
- Tool versions a hook file lists beside its own hooks are a dependency surface current monitoring does not watch — R1 is unmet there until it does.
- A security fix rides the ordinary queue, so a stalled fix must be escalated at the cadence review that consumes the vulnerability reports — no blocking check enforces the escalation ([015](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>) keeps those findings advisory), and without that escalation R6 is only as fast as the queue. If the gate ever grows a security-scanning stage ([014](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>) leaves that open), this record's R6 is its main justification.
- Cadence (weekly proposals) is an operational parameter, not part of the decision: the decision is that being up to date is the default and running old is a choice.
- This record covers libraries inside a runtime, not the runtime itself — the support window for a language version belongs to [031](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/031-runtime-versions-have-a-declared-support-window/index.md>), which leaves the seam for runtime minor bumps unowned.

> [!NOTE]
>
> **Can a dependency deliberately stay old?**
>
> Yes — that is a "hold", and R5 requires recording it: the ignore list carries each held dependency with the reason for its hold. Keeping a dependency old on purpose is a recorded decision; getting old by forgetting is drift.

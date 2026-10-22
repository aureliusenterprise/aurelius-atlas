# 026\. The system can be brought back from a named snapshot

- **Status:** Proposed
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Acceptance trigger (swept 2026-10-19): increment 6.4 lands Elasticsearch snapshots and the first rehearsed restore (R2 is a demonstration, not a document); accepted in that pull request, writing the procedure into the resilience tree as it fills.

Durable data is backed up on a stated schedule, and recovery is a rehearsed path to a named point in time. Data deliberately not backed up is declared disposable in writing — "we would lose that" is a decision, not a discovery.

## Decision

**Backups on a schedule; recovery by rehearsal.** The durable data of the system is protected by backups taken on a stated schedule, and the system can be brought back to a named point in time by a declared procedure, not by improvisation. **Data deliberately not backed up is declared disposable in writing**, so "we would lose that" is a decision rather than a discovery.

Nothing is backed up today and no restore path exists. The only protection in the system is that storage volumes survive a container being recreated — **an accident of tooling, not a decision.** This record is Proposed because the decision, and the mechanism, do not yet exist.

## Context

The system stores things that took time to accumulate: business rows, the configuration that makes it run, the identity data that lets people in. None of it is reproducible from the codebase — **the codebase reproduces the machinery, never the data.** A lost database today is not an outage with a recovery; it is a permanent loss whose size nobody has measured, because nobody has been asked what would be lost.

The system is deliberately runnable in many places — one machine ([006](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), the pipeline, a customer's environment — and each raises the same question: when the storage behind it is lost, what comes back, how much is missing, who performs the return. A host failure, a bad migration, a deleted volume: none require malice, and the system answers all three the same way — **it does not come back.**

Recovery is also a trust question. "What happens to our data if the worst happens?" is a question every operator and many customers ask, and an honest answer requires that someone has decided what is backed up, how often, and how it comes back — **and has practised the coming-back part, because a restore nobody has rehearsed is only a hope.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Every durable store is covered or declared.** Backed up on a stated schedule, or explicitly disposable — no third, unexamined category. |
| **R2** | **A restore produces a working system.** Backups into a clean environment yield a running, consistent system — demonstrated, not assumed. |
| **R3** | **Loss is bounded and stated.** The maximum data a failure can cost is a named number, chosen rather than discovered. |
| **R4** | **Recovery stays inside the boundary.** Backups are operational data and live inside the system's boundary, not a third party's convenience ([016](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/016-the-system-observes-itself-internally/index.md>)). |
| **R5** | **The path is written where it can be found.** The recovery procedure speaks the system's language, not one person's memory. |
| **R6** | **Cheap enough to actually run.** Backups are automatic; the schedule and the success check are the system's job. |
| **R7** | **Recovery time is bounded and stated.** How long a bring-back takes is a named number, measured by rehearsal, not estimated in the incident. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Nothing (the status quo) | Zero cost today; the loss is discovered at the worst moment. R1: the unexamined category is everything. R2: there is nothing to rehearse. The current arrangement, described as an option. |
| Volume snapshots treated as backups | Easy and automatic; R2 as usually practised: a snapshot of a running database is not a consistent database, and a snapshot set nobody has restored is untested until needed. R4's intent, when the snapshot lives wherever the platform puts it. |
| Backups without rehearsed restore | R2: the gap between "we have files" and "the system comes back" is exactly the gap rehearsals find. R5 usually follows: the unpractised restore procedure stays unwritten. |
| Full disaster-recovery infrastructure | A warm standby answers R2 and shrinks R3 — at the cost of operating the system twice. For a system whose recovery point is "everything," the cheap win is backups and a rehearsed restore; a standby is a different decision with a different price, not required here. |
| Do nothing, honestly labelled | Declaring the data disposable is legitimate while every database is a development database — recorded as the decision it is (R1's written declaration), and revisited the first time real data arrives. |

## Tradeoffs

### What it buys

- Loss stops being unbounded and starts being a chosen number (R3), and so does the time to recover (R7).
- Recovery becomes a procedure with a known duration instead of an incident with an unknown one (R2, R5).
- The trust question can be answered honestly to anyone who asks (R1, R4).

### What it costs

- Backups are a standing cost that visibly pays for nothing on every day they are not needed — **which is exactly why they decay. R6 and rehearsal are the defence, and they are the parts people skip.**
- A backup is a copy of the data, so the boundary rule (R4) applies to it too, including who may read it.
- Rehearsing recovery is real time spent on a path the system hopes not to walk.

### Watch

- The recovery point and recovery time numbers belong to whoever accepts this record and **must be named at acceptance, not deferred.**
- Backups of operational signals interact with their stated lifetimes ([025](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/025-data-has-a-stated-lifetime/index.md>)): a backup older than a retention period is a contradiction waiting to be found.
- A restore lands on a schema version, making this record a consumer of the migration path ([023](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/023-storage-schema-changes-by-recorded-migration/index.md>)).
- The placeholder pages on backup and disaster recovery under the architecture section remain headings until this record is accepted and they are written from its answer.

> [!NOTE]
>
> **Why rehearse a restore we hope never to run?**
>
> Because R2 is the requirement rehearsal satisfies, and it cannot be satisfied by a document. Files that exist are not a system that comes back — the gap between them is where unpractised restores fail, and the only honest time to find that gap is a scheduled afternoon, not the incident.

# 025\. Data has a stated lifetime that the system enforces

- **Status:** Proposed
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Acceptance trigger (swept 2026-10-19): increment 6.4 sets retention for catalogue data and operational signals and names the periods the record requires at acceptance; accepted in that pull request.

Every kind of data the system keeps has a stated lifetime, and the system enforces expiry on a schedule. A store with no stated lifetime is a defect: name the lifetime, or own "unbounded" in writing.

## Decision

**Every kind of data has a named lifetime, and expiry is a mechanism.** Data whose lifetime has passed is removed on schedule, without a person deciding per record. A store with no stated lifetime is treated as a defect: **either its lifetime is named, or it is declared unbounded and the cost and risk of that are owned in writing.**

No lifetime is stated or enforced anywhere today — operational data sits at library defaults, one signal's expiry is effectively switched off, and stored business data has no declared lifetime at all. This record is Proposed because the decision has not been made.

## Context

The system accumulates data in several kinds of place, each growing on its own schedule: operational signals from every part, business rows in stores. Growth is not neutral: **storage has a cost that arrives as a bill or a full disk**; old operational data keeps answering questions nobody asked anymore while burying the ones people do ask; and data that can identify people or customers creates obligations that grow with the time it is kept.

The system deliberately keeps all of this inside its own boundary — no operational data ships to a hosted service ([016](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/016-the-system-observes-itself-internally/index.md>)) — which means the organisation that runs the system owns the question of how long the data lives inside that boundary. That decision was named as the operator's problem when the boundary was drawn, and it has not been made since. **The software's own defaults currently make that decision, and one of them is "keep it forever."**

> [!WARNING]
>
> **The default this record replaces: keep it forever**
>
> No expiry is a decision with a date on it — the day it bites is a full disk, a slow query, or an audit question about data the organisation should not hold. The record does not add risk by naming lifetimes; it removes the risk of the unnamed default.

The question this record answers is not which tool expires what. It is **who says how long each kind of data is kept, what enforces the answer, and what happens when the answer changes.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Every kind has a stated lifetime.** The period is written where a person answering "why do you still have this?" can read it. |
| **R2** | **Expiry is automatic.** A mechanism on a schedule enforces the lifetime — nobody remembering to clean up. |
| **R3** | **Lifetimes differ by kind.** Each kind has its own reason to keep or drop; one global number answers three questions badly. |
| **R4** | **The statement is answerable.** "How long do we keep X?" is answered from the system's configuration, not a person's memory. |
| **R5** | **Change is a recorded change.** Extending or shortening is deliberate and reviewable, not a side effect of upgrading a tool. |
| **R6** | **Cheap to keep true.** A new store inherits a stated default lifetime rather than arriving undeclared. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Upstream defaults (status quo) | R1: the lifetime is whatever a vendor chose, which nobody read. R4: the answer requires auditing every tool's configuration. R2 fails in one place today, where the default is effectively no expiry. |
| Keep everything forever | The simplest policy to state and the most expensive to hold: R1's purpose — a lifetime of infinity is the absence of a decision. Cost grows without limit, and exposure of anything personal is maximised. |
| Periodic manual cleanup | R2 by definition, R4: what was pruned and when lives in their notes. R5 in practice: the cleanup skipped during a busy month is a silent policy change. |
| One global retention number | Easy to state and audit; R3: debug traces and customer records do not share a reason to exist, and one number is always wrong for at least one kind — too long for the sensitive, too short for the useful. |
| Do nothing | Costs nothing today and lets every vendor make the decision per upgrade. Every requirement fails by leaving the question unasked — the current state described as a choice. |

## Tradeoffs

### What it buys

- The organisation can answer retention questions about its own data without an audit (R1, R4).
- Storage cost becomes bounded and predictable: growth is matched by enforced expiry (R2).
- The exposure that comes with keeping data is limited to a chosen period (R3); retention changes become visible decisions (R5).

### What it costs

- Enforced expiry destroys data irreversibly: a wrong lifetime is discovered after the fact — **the failure is losing something that mattered**, which argues for starting generous and tightening.
- Every store's expiry is one more mechanism to operate and verify.
- A stated lifetime invites exceptions: they must be refused or recorded, not absorbed.

### Watch

- The boundary inside which these lifetimes apply is drawn by [016](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/016-the-system-observes-itself-internally/index.md>), which names retention as the operator's problem and hands it to this record.
- The lifetime of business rows interacts with schema change ([023](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/023-storage-schema-changes-by-recorded-migration/index.md>)): deleting old rows is easy, deleting old *shapes* is a migration.
- The periods themselves — the actual numbers — belong to whoever owns each kind of data and **must be named when this record is accepted, not later.**
- Queued events: the reasoning for them stands, and the streaming slice that carried them left with the catalogue's scope ([050](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)); if a queue returns, an event lifetime shorter than the slowest consumer's recovery window turns retention into a delivery question owned by [027](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/027-every-stream-carries-a-stated-delivery-guarantee/index.md>).

> [!NOTE]
>
> **Why is 'unbounded' allowed at all?**
>
> Because pretending every store expires is how stores end up expiring by accident. Declaring a store unbounded forces the cheap conversation — cost, exposure, an owner in writing (R1) — that "nobody set a TTL" avoids. The defect is the undeclared default, not the length.

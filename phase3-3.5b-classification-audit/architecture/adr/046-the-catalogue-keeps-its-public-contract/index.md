# 046\. The catalogue keeps its public contract while its implementation is replaced

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Aurelius Enterprise

The metadata catalogue's implementation is being replaced; what users and integrations see is not. The same HTTP interface, the same shapes and error codes, the same screens — an unnamed difference is a defect, a named one a recorded deviation.

## Decision

**The contract is frozen; the implementation moves.** The catalogue's implementation is replaced without changing what its users and integrations see: the same HTTP interface, the same request and response shapes, the same error codes, and the same user interface.

**The old behaviour, including its quirks, is the specification.** A difference visible to a client is allowed only as a named, recorded deviation; anything not named is a defect. Fixing a quirk is a deviation and needs a record, not a quiet improvement.

## Context

The catalogue is used by people through its web interface and by other systems through its HTTP interface: ingestion jobs, lineage collectors, scripts written by data teams.

- **The consumers are outside our control** — and many are not even known to us. Every client that has to change multiplies the cost of the migration and delays the day the old system can be switched off.
- **Replacing the implementation is the goal; replacing the consumers is not.** A replacement that is "mostly compatible" leaves each consumer to discover the differences in production.
- **The current implementation is costly** to run and to change: it needs several separate storage and indexing systems, and the team that maintains it works mostly in a different language.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Existing clients keep working.** A client that works against the current catalogue works against the new one without being changed. |
| **R2** | **The user interface is reused.** People keep the screens they know; no parallel interface has to be built or learned during the migration. |
| **R3** | **Differences are known before they are met.** Every difference a client could observe is listed, with its reason, before it ships. |
| **R4** | **The migration can stop at any increment.** At every point the new system serves a consistent subset of the contract, so the work can pause without leaving a half-changed interface. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Design a new, cleaner interface | R1 and R2: every consumer and the interface must be rewritten, and the migration ends only when the last consumer moves. |
| Undocumented "obvious" fixes | R3: each fix is a surprise for a client that depended on the old behaviour. |
| Run both implementations behind a router indefinitely | R1 holds; doubles operating cost and leaves the old system in place, which is what the migration exists to end. |

## Tradeoffs

### What it buys

- Consumers are untouched; the old system's behaviour is a free, executable specification.
- The migration can be paused at any increment boundary (R4).

### What it costs

- The old interface's design flaws and quirks are inherited, and improving them later is a versioned change, not a refactor.

### Watch

- The contract is verified by comparing behaviour with the reference implementation ([048](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>)).
- Current implementation: the Apache Atlas 2.4.0 REST API (`/api/atlas/v2`, `/api/atlas/admin`) and its two user interfaces, `dashboardv2` and `dashboardv3`; deviations are listed in [Deviations from Apache Atlas](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/conversion/deviations/index.md>).

> [!NOTE]
>
> **The old behaviour has known bugs — why port them?**
>
> Because a client may depend on the quirk, and a fix that arrives unnamed is a breaking change delivered as a bug fix (R3). The quirk is fixed by recording a deviation and shipping it visibly — the same rule that makes the contract trustworthy also makes each improvement auditable.

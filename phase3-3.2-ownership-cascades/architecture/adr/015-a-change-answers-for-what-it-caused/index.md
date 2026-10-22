# 015\. A change answers for what it caused

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

The checks that block a change are exactly the checks about the change itself. Findings about the state of the world are produced, recorded, and reviewed on a cadence — they do not block the change that surfaced them.

## Decision

**Blocking: the change's own findings.** Form, lint, types, the tests and builds it can break, the absence of secrets it introduced. **Advisory: the world's findings.** Vulnerabilities in dependencies, code-quality measurements, coverage levels — produced on every change and on a schedule, recorded where they can be reviewed, not blocking the change that surfaced them.

**The line is causation, not severity.** A person is answerable at merge time for what their change did; the organisation is answerable on a cadence for the condition of everything it already ships. An advisory finding is not ignored — it is evidence for the review that consumes it — and a finding may be **promoted to blocking** when the organisation decides to hold changes to it.

This record settles which findings block a change; where the gate is defined is decided elsewhere ([014](<https://aureliusenterprise.github.io/phase3-3.2-ownership-cascades/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)).

## Context

The organisation runs a growing set of checks — style, static analysis, types, tests, builds, secret scanning, vulnerability scanning, license review, quality analysis, coverage — and each produces findings. At merge time every finding raises the same question: does this stop this change?

**Blocking on everything sounds safest and behaves worst.** A vulnerability in a transitive dependency is not caused by the change under review and cannot be fixed by its author today; blocking on it punishes unrelated work, and the predictable response is to bypass the gate, re-run until green, or hold merges for someone to intervene. **A gate trained to be bypassed stops enforcing the rules it was meant to keep.** Coverage targets have their own failure: satisfied by uninformative tests, the number rises while the protection does not.

> [!WARNING]
>
> **A gate trained to be bypassed**
>
> The decay this record is written against: block on everything and people route around the gate — re-run until green, bypass, hold merges — and the checks that catch real regressions lose their force. The blocking set stays small so that green is the normal outcome and a red gate means what it says.

**Blocking on nothing is the opposite failure:** findings accumulate because nothing forces anyone to look, and the organisation cannot say whether its shipments are getting safer or riskier. The team is small and multi-disciplinary — the same people write changes, see findings, and would absorb the triage — so the arrangement must work without a dedicated review function, and the blocking set must stay small enough to satisfy without ceremony.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The blocking set is what the change caused.** The author can satisfy every blocking check in their own change, without waiting for anyone's fix. |
| **R2** | **The everyday loop stays fast enough to keep.** The blocking set runs on every change without dominating it. |
| **R3** | **Advisory findings are recorded, not discarded.** Durable, attributable to the run, for whoever reviews system state. |
| **R4** | **The state of the world is examined on a schedule.** Not only when a change touches the code that surfaces them. |
| **R5** | **Promotion is a decision.** Advisory → blocking is deliberate and reviewable, so the blocking set stays small on purpose. |
| **R6** | **Cheap to keep true.** A small team runs the whole arrangement with no dedicated triage role. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Block on everything | R1: a finding about a dependency, a legacy file, or a coverage number is not the author's to fix, so merges stall on work someone else owes. R2 as the gate grows — and a gate that blocks the unfixable trains people to bypass it. |
| Block on nothing | R1's purpose: a change that introduces a secret or breaks a type reaches shared history. R3 in spirit: with no ceremony attached, the reports stop being read. |
| Numeric thresholds as gates | R1: the threshold measures the file, not the change — a legacy number blocks an unrelated fix. It buys the measured property, not the real one (a coverage floor is met by tests that assert nothing). R2: the cheapest response is lowering the threshold. |
| Triage every finding before merge | R3 passes, R6 fails: adjudication is standing work a small team cannot fund, and in practice it becomes a rubber stamp — the cost of triage with none of the attention. |
| Do nothing (checks run, results unconsumed) | R4 by default: scans tied to changes miss the world that changes nothing. R3: unclaimed reports decay into noise. |

## Tradeoffs

### What it buys

- Authors are stopped only by what they can fix, so the gate keeps its credibility and its speed (R1, R2).
- The serious findings still arrive — per change and weekly — attached to the artifacts they describe, so the organisation can say what it knew and when (R3, R4).
- The blocking set stays small because growing it is an explicit act (R5).

### What it costs

- Known vulnerabilities sit in shipped artifacts between finding and fix — risk carried deliberately, revisited on the cadence that produces the findings.
- Nothing numeric forces quality upward: improvement depends on the review consuming the reports, not a gate enforcing it.
- The promotion path is a decision the organisation keeps making, not a default it can rest on.

### Watch

- The cadence review is a standing obligation: **the record's premise fails if the reviews stop happening** — and naming the role that holds the review is the organisation's first act under this record. Until it is named, the review is unowned and the record is only half in force.
- The weekly whole-system scan is the safety net for code that changes rarely.
- Integrity checks that block (signed, attested releases) gate the release, not the change — left as they are.
- A secret in history is unrecoverable, which is why secret scanning sits on the blocking side while vulnerability scanning does not.

> [!NOTE]
>
> **Why not block on high-severity vulnerabilities?**
>
> Because severity doesn't fix them. The author can't patch a transitive dependency inside the change under review, so the block stalls the merge without closing the finding — and teaches everyone that the gate is an obstacle to route around. The finding belongs to the cadence review, which can schedule the fix.

# 036\. The delivery plane is a named exception to the data boundary

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

The data boundary protects the running system without exception. The delivery plane may cross it only at named, recorded points: each outside service is a named entry, and a new exit is a new record, not a pipeline edit.

## Decision

**The boundary protects the running system; the delivery plane crosses at named points.** The running system and its operational picture stay inside the boundary without exception. The delivery plane — the pipeline that validates and releases the system — **may** use outside services, and each is a named entry: the tool, the kind of data it receives, and why the system's own tools do not answer. **A delivery tool not on the list may not receive data from the pipeline, and a new entry is a new record, not a pipeline edit.**

This decision was in force before it was written down: the pipeline sends interface snapshots of the user interface to a visual-review service and source metadata to a hosted code-analysis service, while the running system and its traces, metrics, and logs have never left. What this record adds is the principle that makes those two uses deliberate rather than contradictory.

## Context

The system keeps its operational picture inside its own boundary ([016](<https://aureliusenterprise.github.io/phase5-5.2-glossary/architecture/adr/016-the-system-observes-itself-internally/index.md>)): no trace, metric, or log reaches an outside service, so the system runs and is legible wherever it runs, including offline and where data may not leave. That rule was written as a rule about the system, and it still holds without exception.

**The pipeline is a different activity.** It answers questions about the code and interface before they ship — does this change alter a screen a customer relies on, does this source introduce a known flaw — and for those the organisation has chosen hosted services, because the comparison they provide (against every previous screen, against a continuously updated catalogue of known flaws) is not something the system's own tools maintain. Those services receive data: pictures of interfaces, metadata about source.

**The two arrangements sit close enough to be confused for each other.** A reader of the boundary rule alone would expect the pipeline to send nothing anywhere; a reader of the pipeline alone would expect the boundary to be a preference. Neither is true, and **the ambiguity is the risk: the next delivery tool can be added by anyone, and without a stated rule there is no way to tell a considered exception from a leak.**

> [!NOTE]
>
> **Why a named exception, not a weakened rule**
>
> Deleting the boundary for the pipeline, or pretending the pipeline sends nothing, both destroy the ability to say which is which. A named exception keeps the rule absolute — the system sends nothing out — and puts the one sending activity on a list where a reviewer can see it. The record that names an exception is what makes "we checked" answerable.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The boundary is stated by data class, not by tool.** Which data may never leave and which the delivery plane may send, from the rule itself — no tool list needed. |
| **R2** | **The running system is never the exception.** No deployed part sends anything outside; the exception belongs to the pipeline alone. |
| **R3** | **Operational data is never the exception.** Traces, metrics, and logs stay inside in every activity, delivery included. |
| **R4** | **Every crossing is named.** Per outside service: the tool, the data kind, the reason the system's tools don't suffice. |
| **R5** | **Crossing is a recorded act.** A new data-receiving delivery service means a new record; a pipeline change alone cannot open an exit. |
| **R6** | **The system still runs offline.** The exception creates no dependency a machine without network access would miss. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| No exceptions: boundary covers everything | Clean and absolute; fails R4's purpose in the other direction — the pipeline already uses hosted comparison services, so the rule is either false on paper or forces removing tools whose value the organisation chose to keep. **A rule the working pipeline quietly violates teaches readers to ignore it.** |
| Boundary as a preference, per tool | R1 and R5: with no stated principle, every addition is a judgement call, and the difference between a considered exception and an accident is whoever notices. |
| Supersede the boundary entirely | R2 and R3 outright: the system runs offline and in restricted environments because the boundary holds for the running system — dissolving it to legitimise two pipeline services trades portability for convenience. |
| Self-host replacements for both | Keeps every byte inside; fails the reason the services are used: the value is the comparison against history and a maintained external catalogue, and a self-hosted copy of that standing is upkeep the organisation has not chosen to operate. |
| Do nothing (leave the ambiguity) | Free today; R1 and R5 by leaving the boundary readable two ways — the state in which an unlisted exit gets added without anyone deciding anything. |

## Tradeoffs

### What it buys

- The boundary rule can be stated without asterisks, because the exception is a separate, smaller rule (R1).
- The running system keeps every benefit of the boundary — offline, restricted, customer environments (R2, R3, R6).
- The next exit is a decision with a paper trail, not a pull request nobody read (R5).

### What it costs

- Two rules where a reader hoped for one, and the line between "delivery plane" and "system" must be held in every future review.
- Each named service is a dependency the pipeline can fail on and a recipient the organisation must trust with the data class it receives.
- The exception invites pressure to widen it, which R5 exists to slow down.

### Watch

- The current entries: the visual-review service (receives interface snapshots) and the hosted code-analysis service (receives source metadata). **A tool that begins receiving more than its entry states has opened an unrecorded exit** — each entry's data kind is a standing obligation.
- Whether the gate enforces those services' findings is a question the gate and causation records answer ([014](<https://aureliusenterprise.github.io/phase5-5.2-glossary/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>), [015](<https://aureliusenterprise.github.io/phase5-5.2-glossary/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)).
- This record narrows nothing about the boundary itself — [016](<https://aureliusenterprise.github.io/phase5-5.2-glossary/architecture/adr/016-the-system-observes-itself-internally/index.md>)'s rule stands as written, and any change to it is a supersession, not an edit.

> [!NOTE]
>
> **Why not just keep every byte inside?**
>
> Because the hosted services sell comparison, not storage: every previous screen, a continuously updated flaw catalogue. Self-hosting that standing is an upkeep the organisation has declined (the alternatives table), and banning them would make the boundary rule false on paper — a rule the working pipeline violates without anyone noticing (the first alternative). Naming the two exits is what keeps the rule both true and absolute where it counts.

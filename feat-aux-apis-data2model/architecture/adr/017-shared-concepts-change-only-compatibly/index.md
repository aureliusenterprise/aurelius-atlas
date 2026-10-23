# 017\. Shared concepts change only in ways that keep readers working

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

A change to a shared concept must leave every existing reader working without being changed first. Additive change is the default; a breaking change is a new version carried beside the old one, never an edit to what readers consume.

## Decision

**The compatibility rule sets the direction.** A concept change is permitted only where it leaves every existing reader of the concept working unmodified. Additive change — a new optional element — is the default direction; a change that would break a reader is a **new version**, carried alongside the old one for a stated period, never an edit to what readers already consume.

**The rule is checked where it can be checked** — a violating change is refused, not warned about — and where it cannot yet be checked, the change carries the same obligation by review.

This record settles the direction concepts may move in; where the canonical definition lives and how copies are kept honest is decided elsewhere ([004](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/004-one-shared-domain-model/index.md>)).

## Context

Business concepts are consumed the moment they are defined: records carrying them sit in streams waiting to be read, rows persist for years, and receivers outside the organisation parse them on their own schedule. **A concept has consumers the organisation does not control and cannot pause** — data in motion, data stored, partners integrated.

That is what separates concept change from code change. Code and its callers are updated together in one change; a concept's older readers cannot be updated before the change lands, because they run elsewhere or the data they read was written earlier. **A concept edited in a breaking direction does not fail at the edit — it fails later**, at whichever reader cannot parse what arrived, far from the change that caused it.

One canonical definition per concept ([004](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/004-one-shared-domain-model/index.md>)) made every consumer depend on one statement — that is the point — which means the statement now needs a rule for how it may change: a single definition edited freely concentrates exactly the breakage it was meant to prevent. The guidance so far recommends a compatibility strategy without naming who enforces it or what a genuine break becomes, so the rule lives nowhere and every concept change re-decides it.

> [!NOTE]
>
> **Why the rule is about concepts, not code**
>
> A code change and its callers ship together, so a break fails the build. A concept — a type's meaning, an enum's set, a field's shape — is read by data written yesterday and by processes the release does not reach. The edit passes every check; the failure happens later, at a reader far from the change. That lag is why compatibility needs its own rule, and why the single canonical definition ([004](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/004-one-shared-domain-model/index.md>)) concentrates the breakage it needs to prevent.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Existing readers keep working.** Every reader built against the earlier version still reads what arrives, unmodified. |
| **R2** | **Old data stays readable.** Records written before the change remain parseable afterwards, as long as they exist. |
| **R3** | **Breakage is a new version, not an edit.** The old version keeps being served while the new is adopted, with a stated path and period. |
| **R4** | **The rule is enforced, not advised.** A violating change is stopped by a check, not left to whoever remembers. |
| **R5** | **The rule is stated where consumers can read it.** What may change and what is stable, without asking anyone. |
| **R6** | **Cheap to keep true.** Honouring the rule costs a small routine step, not a ceremony. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Free change: edit whenever needed | R1 and R2 by construction: readers built against the old shape meet data they cannot parse, stored records become unreadable — the failure lands at the worst time, far from its cause. R5: nothing tells a consumer when the ground moved. |
| Freeze: no breaking changes ever | R3's purpose: businesses do need changes readers cannot absorb — a removed field, a retyped identifier — and a rule with no exit is quietly abandoned the first time one is needed, taking the rest of the rule with it. |
| Warn but don't stop | R4: a warning that merges anyway is the same arrangement as no rule, differing only in logs. R5: "ask the elders" is not a stated rule. |
| Version everything up front | R1 and R2 pass, R6 fails: the routine majority (additive changes) would each spawn a parallel version to maintain. R5 degrades: consumers face a version matrix where one evolving concept would serve. |
| Do nothing (keep recommending a strategy) | Where the repository stands, so it costs nothing. R4 by default: the recommendation has no enforcement point. R3: no stated path for the breaking change guidance cannot prevent. |

## Tradeoffs

### What it buys

- Concept changes stop being an incident risk: readers built earlier keep working, so streams and stored data survive the change (R1, R2).
- The rare breaking need has a named route instead of an exception made under pressure (R3).
- Consumers integrate against a stated contract, not an observed habit (R5).

### What it costs

- The everyday direction of change is widened rather than deepened: reshaping a concept is a versioned migration — slower than an edit, and honestly sometimes felt as bureaucracy.
- Running two versions side by side is real cost that must end on a stated date or become permanent.
- Enforcement needs a checking mechanism the organisation does not fully have yet; until it exists the rule leans on review — **a gap to close, not a tolerated state.**

### Watch

- The compatibility level at which the registry refuses changes is this rule's enforcement point and must be set deliberately, not inherited from a default — until set, R4 is aspirational at that boundary.
- Hand-kept representations of a concept are checked against this rule by review until a check exists — the obligation [004](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/004-one-shared-domain-model/index.md>) already carries. Storage sinks configured not to follow concept changes are deliberate; keeping table and concept in step is then a named migration task.
- The period an old version runs alongside a new one is named by the concept's owner at the time of the break, not later.
- Dependent set — records that lean on this rule without restating it: [027](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/027-every-stream-carries-a-stated-delivery-guarantee/index.md>) (how a stream behaves), [030](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/030-interfaces-between-parts-are-verified-not-assumed/index.md>) (interfaces verified against this rule), [032](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/032-shared-streams-are-named-by-a-declared-convention/index.md>) (the name a breaking change travels under). If this record is superseded, those three are the set to re-check.

> [!NOTE]
>
> **Why carry two versions instead of a migration window?**
>
> Because the readers are outside. A migration window works when you control both ends and can schedule the cutover; here the data is in streams, stored rows, and partner systems that parse on their own schedule. The old version keeps answering them while the new one is adopted on their clock, not the editor's.

# 004\. One shared domain model serves streaming and storage

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Each shared business concept has exactly one canonical definition, held outside any technology. Copies elsewhere are generated from it where generation is possible and checked against it where it isn't — a copy that is neither is a violation, not a tolerated variant.

## Decision

**One canonical definition per concept**, held outside any single technology. Representations of the concept elsewhere are generated from it where generation is possible and checked against it where it is not.

**The same definition serves the concept in motion and at rest:** one statement of what an order *is* governs the records that stream between systems and the rows that persist in storage. Changing the concept is one change, and its consequences are visible everywhere at once.

## Context

The business system moves the same concepts across boundaries — entered on a screen, processed by a service, streamed between services, persisted in a database. Each place speaks its technology's dialect, and left to itself each keeps its own description of the concept.

The cost falls due at every boundary. When two places describe one concept differently, someone translates between them, and translation code is where meaning is quietly lost: a field dropped, a meaning shifted, a field added in one place and unknown in another. These surface as data-integrity incidents and integration work — months after the change that caused them, owned by whoever is nearest the symptom.

A concept also has to survive transport between systems not built together, so its description must be legible to receivers that do not share the producing codebase.

The decision is where a shared concept's definition lives, and how its copies are kept honest.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One concept, one definition.** One authoritative statement per concept, owned by no single consumer. |
| **R2** | **Drift is detected, not discovered.** A mismatch fails a build or test — not a customer, later. |
| **R3** | **One definition in motion and at rest.** A record in motion and a row at rest cannot mean different things. |
| **R4** | **Change is one edit.** Evolving a concept is a single change whose full impact is visible in one review. |
| **R5** | **Portable across boundaries.** Consumable by systems outside the codebase without sharing code. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Per-stack models with mapping layers | R1: as many definitions as stacks. R2 structurally: a mapping layer absorbs drift rather than detecting it, so divergence becomes a runtime difference. R4: one coordinated edit per stack, per change. |
| The storage schema as the contract | R2 for what matters most: a schema constrains rows, not records in motion, so streaming consumers evolve against a contract they never consult. R5: binds a business concept to one storage technology. |
| Per-consumer schemas, negotiated at integration | R1 immediately: the concept is defined once per integration. R2: nothing checks that two negotiated formats still describe one concept a year later. |
| Do nothing (each stack keeps its own model) | R2 by default: drift is found by whoever notices the data disagreeing. R4 by default: every concept change is N edits in N reviews by N people. |

## Tradeoffs

### What it buys

- A concept change is one reviewed change with visible blast radius (R4).
- Representations cannot silently disagree: the generable ones are generated, the rest are checked (R2).
- The concept travels outside the organisation as a plain artifact, not a library in a company language (R5).

### What it costs

- The canonical definition becomes a shared dependency: changing it touches every consumer, so concept changes need an evolution policy (what may be added, what breaks consumers) that per-stack models never had to write down.
- Some consumers need only a projection of a concept, and hand-maintaining that projection is exactly the copy this record exists to eliminate.

### Watch

- Representations that can't be generated today — a hand-written model in a dynamic language, a type in the interface, an inline schema in a flow tool — are kept in step by convention until a check exists. Under this record that is a gap to close, not a tolerated state: a representation found out of step is regenerated, not reconciled by hand.

> [!NOTE]
>
> **Convention is a gap, not a state**
>
> The sentence above is the record's sharpest edge: a hand-written copy that no check verifies is drift waiting to happen, and the record refuses to accept it as normal. The closing mechanism is interface verification ([030](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/030-interfaces-between-parts-are-verified-not-assumed/index.md>)) — until a check exists, treat every unverified copy as a to-do with a due date.

- For interfaces between parts, the verification rule ([030](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/030-interfaces-between-parts-are-verified-not-assumed/index.md>)) takes it up — a representation nobody checks against is where drift starts.

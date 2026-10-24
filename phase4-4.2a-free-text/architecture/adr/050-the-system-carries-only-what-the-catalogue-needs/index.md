# 050\. The system carries only the capabilities the catalogue needs

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Aurelius Enterprise

Every template capability the catalogue does not use is removed — streaming, serverless, the Java build, and in time the template's examples and relational database. This is a named deviation from the template spine: the catalogue's own parts become the spine.

## Decision

**Remove what is unused.** Every template capability the catalogue does not use is removed from this codebase: the event streaming slice, the serverless slice, the Java build, and — once their replacements exist — the template's example service, example screen, example library, and relational database.

**A named deviation from the spine.** The template's spine rule ([002](<https://aureliusenterprise.github.io/phase4-4.2a-free-text/architecture/adr/002-modules-are-removable-slices/index.md>)) names a fixed keep-list; here the catalogue's own server, dashboard, and search store become the spine, and that swap is declared, not smuggled.

## Context

The codebase was created from a template that demonstrates many capabilities at once.

- **Each kept capability costs.** Build time, dependency updates, security scanning, and reader attention — and it suggests to newcomers that it is part of the product.
- **The catalogue's needs are narrow.** One HTTP service, one user interface, one data store ([047](<https://aureliusenterprise.github.io/phase4-4.2a-free-text/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)), the shared identity provider, and observability.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **What is here is used.** Every project in the repository serves the catalogue or its delivery workflow. |
| **R2** | **Template updates stay mergeable.** The workflow parts of the template (pipeline, quality gate, documentation, secrets) stay recognisable so updates can be merged. |
| **R3** | **Nothing is removed before it is replaced.** The repository builds and its tests pass after every removal. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Keep every template slice | R1: unused code is maintained, scanned, and misread as product. |
| Start from an empty repository, copy the workflow | R2: template improvements can no longer be merged. |

## Tradeoffs

### What it buys

- A smaller, honest codebase; a faster pipeline; fewer dependency alerts.

### What it costs

- Re-adding event streaming later — for example, to accept Atlas hook notifications — means restoring the slice from the template.

### Watch

- Increment 0.1 removes the streaming and serverless slices and the Java build; increment 0.5 removes the example service, screen, library, and relational database when the Atlas server and dashboard replace them.
- Until then, those examples remain a named deviation under this record.

> [!NOTE]
>
> **The examples are harmless — why remove them?**
>
> Unused code is never harmless: it is built, scanned, updated, and defended in review, and a newcomer cannot tell an example from a feature (R1). Keeping them only until replacements exist is the disciplined version of the same rule — R3 sets the order, so the repository never loses a capability before it has its replacement.

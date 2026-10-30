# 047\. One search store is the only system of record for metadata

- **Status:** Accepted (increment 0.2 provides the store in the spine)
- **Date:** 2026-10-09
- **Deciders:** Aurelius Enterprise

All catalogue data lives in a single search store that is both the system of record and the search index — no graph database, relational database, or second index to keep in step. The store's two gaps (transactions, graph traversal) become application concerns, each recorded.

## Decision

**One store, two jobs.** All catalogue data — type definitions, entities, relationships, classifications, glossaries, audit events — lives in a single search store, which is both the system of record and the search index. There is no separate graph database, relational database, or index to keep in step with it.

**The store has known gaps.** It has no multi-record transactions and no native graph traversal. Where the catalogue needs either, the application provides it, and each such place is recorded as a design decision.

## Context

The current catalogue keeps its data in a graph database, which itself runs on a wide-column store, plus a separate full-text index, plus a coordination service.

- **Each system is a system.** Deploy, secure, back up, upgrade, and understand — five verbs per store, paid continuously.
- **The daily workload is retrieval.** Most of the catalogue's daily use is search and retrieval of individual records; graph traversal matters for lineage and for propagating classifications, but on graphs that are shallow compared with what a graph database is built for.
- **One machine is a requirement.** The team must be able to run the whole system on one machine for development ([006](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), and operations must stay affordable for small installations.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One thing to operate.** A deployment has one stateful data service to run, back up and restore. |
| **R2** | **Search is first-class.** Full-text and attribute search, facets and suggestions perform well without a second copy of the data. |
| **R3** | **No drift between copies.** There is no second store that can disagree with the first. |
| **R4** | **Graph questions remain answerable.** Lineage and classification propagation are computed correctly for the depths the catalogue supports. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Graph database plus search index (the current design) | R4 natively; R1 and R3: two or more stores to operate and keep consistent. |
| Relational database plus search index | R4 with recursive queries; R1 and R3 in the same way. |
| Relational database only | R1, R3, R4; weakens R2: full-text relevance, facets, and suggestions are the catalogue's most used features. |

## Tradeoffs

### What it buys

- One store to operate, back up, and secure; search is native; no copies to reconcile.

### What it costs

- Consistency across records and multi-hop traversal become application concerns, with their own tests and failure modes.
- Very deep lineage is slower than in a graph database.

### Watch

- The storage layout, identifier strategy, consistency model, and traversal strategy are design-log entries in [the conversion ledger](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/conversion/design-log/index.md>).
- Current implementation: Elasticsearch 9.

> [!NOTE]
>
> **Isn't a catalogue 'obviously' relational data?**
>
> For the workload that dominates — search, facets, retrieval of individual records — the relational answer is the weakest one: it buys R1 and R3 by giving up R2, the catalogue's most used features. The relational strengths (transactions, joins) are exactly the two gaps the application layer covers, once each, visibly.

# Architecture

Aurelius Atlas helps an organisation discover, understand, and trust its data — and stays easy to run, because a catalogue that is expensive to operate governs nothing. The engine behind that is a Python re-implementation of Apache Atlas 2.4.0 with Elasticsearch 9 as its only store. The two **working records** of the system are the [conversion roadmap](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/conversion/index.md>) — the increments, their status and their semantics specs — and the [architecture decisions](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/index.md>), the ADRs that constrain every change. Both are kept current by every pull request.

> [!NOTE]
>
> **What is a 'working record'?**
>
> A page that states the system's current truth and is updated by the pull requests that change it — unlike a reference page, which describes a planned state and is written once, by the increment that builds it. If a working record and the code disagree, the record is wrong.

The remaining trees are the **reference architecture**: they describe the system as it will stand when the plan is done. They are written increment by increment — each page names the increment that writes it, so a page is written in the pull request of that increment, while its facts are fresh (ADR 051). Pages not yet written carry a `Planned` marker naming their increment; the convention is in [Documentation](<https://aureliusenterprise.github.io/feat-webapp-landing/contributor-guide/documentation/#architecture-pages>).

> [!NOTE]
>
> **Why two kinds of pages**
>
> A mid-conversion system has no single accurate description: the code is the plan partly built. Splitting the records (what is true now, maintained by every PR) from the reference (what will be true, written as each increment lands) keeps both statements honest — each page names the increment, spec, or code that owns its facts.

## The trees

| Tree | Subject | Written by |
| --- | --- | --- |
| [Vision &amp; Strategy](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/vision-and-strategy/index.md>) | Why the system exists, for whom, and where it is going | written (ADRs 046–052, the roadmap) |
| [Data Lifecycle Management](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-lifecycle-management/index.md>) | How catalogue data enters, lives, is shared, and is retired | 0.2 → 6.3, per page |
| [Data Governance](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-governance/index.md>) | Types, lineage, quality, ownership, auditability | 1.6 → 6.2, per page |
| [Platform](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/platform/index.md>) | Connectivity, delivery, observability, resilience, security | 0.2 → 6.4, per page |

Each tree index page carries its own per-page filling map.

These pages state the system's properties by **role** — the search store, the identity provider, the collector — so the description survives a change of product. The knobs, ports, and commands of each part live in its own documentation: the [API Reference](<https://aureliusenterprise.github.io/feat-webapp-landing/api-reference/index.md>) pages (design documentation per component), the [Contributor Guide](<https://aureliusenterprise.github.io/feat-webapp-landing/contributor-guide/index.md>) (cross-cutting how-tos), and each `dev/` slice's README (development topology).

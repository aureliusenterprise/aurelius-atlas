# Stakeholder Analysis

Whom Aurelius Atlas serves, and what each of them needs the system to be.

| Stakeholder | Needs | Where it is answered |
| --- | --- | --- |
| Business users | Find data and its context in seconds; see who to ask; a familiar, friendly interface | Dashboard served at `/` and `/n/` (increment 0.6), search in phase 4 |
| Data stewards and owners | Know which assets they are accountable for; classify data and record its quality | Classifications in 3.3, glossary in 5.2, [roles](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/data-governance/roles-and-responsibilities/index.md>) in 6.2 |
| Compliance and audit | Sensitive data identified, access controlled, changes on the record (GDPR and similar rules) | Phase 6 (identity provider, authorizer, audit), [security tree](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/platform/security/index.md>) |
| Analysts and data scientists | Lineage and impact analysis; trustworthy, fit-for-purpose data | Lineage in 5.1, quality signals in 5.2/5.3 |
| Migrating Atlas users | Existing clients and integrations keep working; behaviour differences disclosed | ADR 046, [deviations](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/conversion/deviations/index.md>), export/import in 6.3 |
| Security and compliance reviewers | Identity, authorization, audit trail, encryption with named owners | Phase 6, [security tree](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/platform/security/index.md>) |
| Catalogue operators | Run the whole system on one machine; one store to back up; loud failure | ADR 006, ADR 047, [resilience tree](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/platform/resilience/index.md>) |
| The maintaining team | Every rule has a spec and a test; decisions are recorded where made | ADR 051, ADR 056, this ledger |
| AI coding agents | Nearest-first instructions, specs as the source of behaviour | ADR 022, per-project `AGENTS.md` |

> [!NOTE]
>
> **Why AI coding agents are a stakeholder**
>
> The repository is changed routinely by automated agents as well as by people, so they are a real consumer of its documentation: colocated `AGENTS.md` files give them nearest-first instructions, and the specs give them the source of behaviour to code against ([ADR 022](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/022-the-codebase-explains-itself-to-its-agents/index.md>)). Serving them well is a documentation requirement like serving a new hire well — the same material answers for both.

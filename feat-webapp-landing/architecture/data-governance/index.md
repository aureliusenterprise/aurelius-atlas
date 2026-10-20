# Data Governance

Governance in the terms the business uses: people discover and understand data, know who is accountable for it, see how it flows and how sensitive it is, and can prove all of it. Concretely, that is how Aurelius Atlas describes, classifies, connects, and accounts for data — the catalogue's own subject: the type system, lineage, glossary, classifications, and audit trail. The rules live in the increment [semantics specs](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/conversion/increments/index.md>); these pages assemble them into the governance view.

| Page | Scope | Written by |
| --- | --- | --- |
| [Roles &amp; Responsibilities](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-governance/roles-and-responsibilities/index.md>) | Who owns and who may act: authorizer roles, dataset ownership | 6.2 (ADR 042) |
| [Data Dictionary](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-governance/data-dictionary/index.md>) | The type system as the catalogue's dictionary: typedefs, built-in models, inheritance | 1.6 (material exists from 1.1–1.5) |
| [Data Quality](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-governance/data-quality/index.md>) | Glossary, terms, business metadata, labels as quality signals | 5.2, 5.3 |
| [Data Lineage](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-governance/data-lineage/index.md>) | Processes, inputs/outputs, depth and direction, on-demand lineage | 5.1 |
| [Compliance &amp; Auditability](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/data-governance/compliance-and-auditability/index.md>) | Entity audit events, classifications with validity, audit REST | 3.5, 6.2 |

> [!NOTE]
>
> **Every page here is Planned — where do I read the rules?**
>
> In the increment specs, which are written with the code and are the authority ([semantics specs](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/conversion/increments/index.md>)); the dictionary's material, for example, exists from increments 1.1–1.5 even though its page lands with 1.6. A `Planned` marker names the increment whose spec to read instead.

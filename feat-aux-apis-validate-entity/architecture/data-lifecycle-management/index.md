# Data Lifecycle Management

A data asset's journey in the catalogue: getting discovered and registered, staying current, being shared with the right people, and being retired safely. In system terms, how catalogue data enters Aurelius Atlas, where it lives, how it is processed, shared, and retired. The rules themselves live in the increment [semantics specs](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/conversion/increments/index.md>); these pages assemble them into the lifecycle view.

| Page | Scope | Written by |
| --- | --- | --- |
| [Data Collection](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/data-lifecycle-management/data-collection/index.md>) | Ingestion: entity/typedef create and update, bulk, headers | 2.4 (entity write REST) |
| [Data Storage](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/data-lifecycle-management/data-storage/index.md>) | One search store as system of record: layout, identities, versioning | written (0.2/1.4); entity layout with 2.2 |
| [Data Processing](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/data-lifecycle-management/data-processing/index.md>) | Classification propagation, audits, cascades | 3.2–3.5 |
| [Data Sharing](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/data-lifecycle-management/data-sharing/index.md>) | Export ZIP, import, migration of an existing Atlas | 6.3 |
| [Data Archiving](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/data-lifecycle-management/data-archiving/index.md>) | Soft delete, purge, retention of the store; snapshots | 2.5, 6.4 |

> [!NOTE]
>
> **Most of these pages are Planned — where are the rules today?**
>
> In the increment specs, which are written with the code and are the authority ([semantics specs](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/conversion/increments/index.md>)). A lifecycle page assembles rules that already exist into the lifecycle view once the increment that fills it lands; until then the `Planned` marker names the increment to read instead.

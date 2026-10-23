# Data Storage

All catalogue data lives in one search store — the system of record and the search index at once ([ADR 047](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)). There is no graph database, relational store, or separate index to keep in step. The current implementation is Elasticsearch 9, reached through the store library; its knobs and mechanics are in the [store's design documentation](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/api-reference/libs/python/aurelius-atlas-store-es/index.md>).

> [!NOTE]
>
> **Why is one store the only store?**
>
> Catalogue data answers five verbs — write, read, search, traverse, classify — and ADR 047 graded each candidate arrangement by them: every extra store adds a second place where the same facts must agree, plus its own backup, upgrade, and monitoring. One store that serves all five verbs turns consistency into a single-writer problem and self-hosting into running one service and one store.

## The store today (increments 0.2, 1.4)

The store library owns the client: the link is TLS-only with certificate verification and credentials — an unencrypted endpoint is rejected at settings validation, before the service opens. A deployment runs and monitors the cluster; the development arrangement runs one (`dev/elasticsearch`).

Type definitions move as **one unit of storage**: the store replaces all definitions whole under a concurrency guard, so a change to several definitions lands atomically, with one version number for all types ([DD-028](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-028-the-type-definitions-are-one-elasticsearch-document>)). This is a property the type system needs — Atlas changes several definitions in one transaction, a create stores all of a request or none — stated here, implemented there: the alias names, write-index mechanics, and size trade-offs are the design documentation's. The unit loads into the type registry when the service starts (rule TDS-12). The definitions are not searched — searching over catalogue entries arrives with search in increment 4.1.

## The entity layout (increment 2.2)

Every catalogue entry (an entity of any type) is **one record, found by its identifier**: a random UUID, as Atlas's clients already know it ([DD-044](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-044-a-guid-is-a-random-uuid>)). A read by identifier always sees the last write; nothing waits for the search index to catch up ([DD-043](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-043-entities-are-documents-of-one-index-their-attributes-under-qualified-names>)). Attribute values are kept with their exact digits and become searchable when search arrives (4.1). A value that is a structure is kept inside its entry; a link to another entry is kept as that entry's identifier, so a renamed entry is never shown under its old name ([DD-049](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-049-attribute-values-are-stored-normalised-a-struct-inline-a-reference-as-a-guid>)). Each entry also lists, searchably, the identifiers of the entries it links to, so that deleting an entry finds the entries that link to it ([DD-057](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-057-entities-referring-to-one-are-found-through-an-indexed-field-of-guids>)). A deleted entry is kept, marked deleted, until it is purged; a purge or a hard delete removes it within the same all-or-nothing write as everything else the request changes ([DD-056](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-056-an-entity-write-also-removes-documents-journaled-like-the-others>)).

The store gives the catalogue the three guarantees its graph database gave Atlas, each recorded:

- **A unique value is held once per type.** Two entries of one type cannot share a `qualifiedName`, even when two servers try at the same instant; a deleted entry gives its value up ([DD-045](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-045-unique-values-are-reserved-by-create-only-documents>)).
- **A write of several entries succeeds or fails as a whole**, also when a server dies part-way: a journal lets the next start undo what was left half done. While a write is in flight another reader may see part of it ([DD-046](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-046-a-multi-entity-write-is-all-or-nothing-through-a-journal>), DV-16).
- **Concurrent changes are detected, not lost.** A change is written only over the version it was read in ([DD-047](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/conversion/design-log/#dd-047-entities-are-written-conditionally-on-their-elasticsearch-version>)).

The concrete indices, mappings and write steps are the [core library's design documentation](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/api-reference/libs/python/aurelius-atlas-core/index.md>).

## Rules that bind storage

- Schema changes go by recorded migration, data moved rather than replaced ([ADR 023](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/adr/023-storage-schema-changes-by-recorded-migration/index.md>)).
- Data has a stated lifetime the system enforces; purged data is gone ([ADR 025](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/adr/025-data-has-a-stated-lifetime/index.md>), delete semantics in 2.5).
- Recovery is from a named snapshot ([ADR 026](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>), snapshots in 6.4).
- Encryption in transit is TLS with verification ([data encryption](<https://aureliusenterprise.github.io/phase4-4.1a-entity-search/architecture/platform/security/data-encryption/index.md>)); at rest belongs to the deployment.

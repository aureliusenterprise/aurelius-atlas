# Data Storage

All catalogue data lives in one search store — the system of record and the search index at once
([ADR 047](../adr/047-one-search-store-is-the-system-of-record.md)). There is no graph
database, relational store, or separate index to keep in step. The current implementation is
Elasticsearch 9, reached through the store library; its knobs and mechanics are in the
[store's design documentation](../../api-reference/libs/python/aurelius-atlas-store-es.md).

??? QUESTION "Why is one store the only store?"

    Catalogue data answers five verbs — write, read, search, traverse, classify — and ADR 047
    graded each candidate arrangement by them: every extra store adds a second place where the
    same facts must agree, plus its own backup, upgrade, and monitoring. One store that serves
    all five verbs turns consistency into a single-writer problem and self-hosting into running
    one service and one store.

## The store today (increments 0.2, 1.4)

The store library owns the client: the link is TLS-only with certificate verification and
credentials — an unencrypted endpoint is rejected at settings validation, before the service
opens. A deployment runs and monitors the cluster; the development arrangement runs one
(`dev/elasticsearch`).

Type definitions move as **one unit of storage**: the store replaces all definitions whole under a
concurrency guard, so a change to several definitions lands atomically, with one version number
for all types ([DD-028](../conversion/design-log.md#dd-028-the-type-definitions-are-one-elasticsearch-document)).
This is a property the type system needs — Atlas changes several definitions in one transaction,
a create stores all of a request or none — stated here, implemented there: the alias names,
write-index mechanics, and size trade-offs are the design documentation's. The unit loads into
the type registry when the service starts (rule TDS-12). The definitions are not searched —
searching over catalogue entries arrives with the entity layout in increment 2.2.

## The entity layout (increment 2.2)

The roadmap states what 2.2 adds: the entity layout, identities, unique-attribute lookups, and
optimistic versioning — the port of `AtlasEntityStoreV2`. When it lands, this page states the
properties — layout, sharding and refresh behaviour, the versioning protocol — and the concrete
mapping goes to the store's design documentation.

## Rules that bind storage

- Schema changes go by recorded migration, data moved rather than replaced
  ([ADR 023](../adr/023-storage-schema-changes-by-recorded-migration.md)).
- Data has a stated lifetime the system enforces; purged data is gone
  ([ADR 025](../adr/025-data-has-a-stated-lifetime.md), delete semantics in 2.5).
- Recovery is from a named snapshot ([ADR 026](../adr/026-the-system-can-be-brought-back-from-a-named-snapshot.md),
  snapshots in 6.4).
- Encryption in transit is TLS with verification
  ([data encryption](../platform/security/data-encryption.md)); at rest belongs to the deployment.

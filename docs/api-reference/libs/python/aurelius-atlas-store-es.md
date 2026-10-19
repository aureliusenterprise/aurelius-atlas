# aurelius-atlas-store-es

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-store-es)

Elasticsearch access for Aurelius Atlas: settings, client lifecycle, version check and health check.

## Installation

```toml
dependencies = ["aurelius-atlas-store-es"]

[tool.uv.sources.aurelius-atlas-store-es]
workspace = true
```

Tests that need a server add `aurelius-atlas-store-es[testing]` to their dev dependencies.

## Design

The technology-specific detail of the store. The property it keeps — one search store as the
system of record — is [ADR 047](../../../architecture/adr/047-one-search-store-is-the-system-of-record.md);
the layout decisions are recorded as
[DD-005](../../../architecture/conversion/design-log.md#dd-005-the-store-uses-the-official-async-elasticsearch-client),
[DD-008](../../../architecture/conversion/design-log.md#dd-008-a-yellow-cluster-is-healthy) and
[DD-028](../../../architecture/conversion/design-log.md#dd-028-the-type-definitions-are-one-elasticsearch-document).

**Client.** One official async Elasticsearch client per store, created from `StoreSettings` and
owned by the store's lifespan. Connections are always HTTPS with certificate verification
(`ca_certs`, `verify_certs=True`) plus basic auth; plain-`http` hosts are rejected by settings
validation, before a connection is opened — pointing the server at a stock local Elasticsearch
(which serves plaintext by default) fails with a validation message, not a connection error.
`dev/elasticsearch` is the TLS-served store made for this, with the CA the server trusts. The
store fails fast unless the server reports Elasticsearch 9.

**Health.** `health()` never raises: green **and yellow** both count as up — a single-node dev
cluster is permanently yellow, and yellow means every primary shard serves
([DD-008](../../../architecture/conversion/design-log.md#dd-008-a-yellow-cluster-is-healthy)).

**Type-definition layout (increment 1.4).** All type definitions live in **one** document, behind
the alias `aurelius-atlas-typedefs`, which always names the current write index
(`aurelius-atlas-typedefs-000001`). The alias is created when the store first opens, refreshed on
every write, and loaded into the type registry at server start (rule TDS-12). The document is
replaced whole under an `if_seq_no` guard: Atlas changes several definitions in one graph
transaction, and Elasticsearch has no transaction across documents, so atomicity costs one version
number for all types and serialised type changes. The built-in model is about 1 MB; a deployment
with tens of thousands of custom types revisits the choice (DD-028). The document is not searched —
searching over catalogue entries arrives with the entity index layout in increment 2.2.

**Test fixtures.** `testing.fake` is a stand-in client for unit tests (no extra needed);
`testing.container` starts a TLS-enabled Elasticsearch through testcontainers, with an ephemeral
per-run certificate authority.

## Documentation

::: aurelius_atlas_store_es

::: aurelius_atlas_store_es.testing.fake

::: aurelius_atlas_store_es.testing.container

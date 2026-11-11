# 058\. A new catalogue starts with the m4i data dictionary types

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Aurelius Enterprise

## Decision

Every Aurelius Atlas installation holds the m4i data dictionary types from its first start: the data domains, data entities, data attributes, fields, datasets, collections, systems, people, data quality and governance quality rules, sources and generic processes of `m4i_atlas_core`, their relationships, and the five classifications `PII`, `key_data`, `low_risk`, `medium_risk` and `high_risk`. The server creates them at start-up, after Apache Atlas's own types, as it creates those. An operator may turn this off; types already stored stay.

The kubernetes and connector types of `m4i_atlas_core` are not part of this decision. They stay with the products that describe those systems.

## Context

Aurelius Atlas is used as a data governance catalogue, and its users describe their data in the m4i data dictionary. Aurelius applications read and write those types, the lineage model and data-to-model among them. The catalogue's existing data, its sample data included, is in them. Until now, a new installation was empty of them until someone ran a separate script against it. A catalogue without them cannot take an import of existing data until the types are created, and the applications built on them fail against it.

The catalogue keeps Apache Atlas's public contract ([ADR 046](<https://aureliusenterprise.github.io/fix-11-5b-mode-in-settings/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). A new Apache Atlas holds only its own types.

## Requirements

- R1: A new installation can take the existing m4i data, and serve the applications built on it, without a manual step.
- R2: An existing installation that already holds the types keeps them and its data unchanged.
- R3: The types are the ones the existing data uses, so an import of it creates no type.
- R4: An installation that should hold only Apache Atlas's types can have that.
- R5: Every API behaviour of Apache Atlas stays as it is; only the set of types differs.

## Alternatives

- **Leave the types to a script run after installing**, as `m4i_atlas_core` does. It fails R1: someone must remember it, with credentials, after every new installation.
- **Every m4i type, the kubernetes and connector groups included.** It meets R1 to R5, but it gives every catalogue types for systems most users don't describe, and those groups change with those systems, not with the data dictionary.
- **Ship the types in each application that needs them.** Each application would create them on first use. It fails R1 for an import, which comes before any application, and spreads one model over several owners.

## Tradeoffs

- **Positive:** a new catalogue is ready for the m4i data and its applications. The types are versioned with the server, so a change to them ships as a release.
- **Negative:** a new catalogue lists types a new Apache Atlas doesn't ([DV-139](<https://aureliusenterprise.github.io/fix-11-5b-mode-in-settings/architecture/conversion/deviations/index.md>)). `PII` and the four risk classifications are taken names, so a client that creates its own classification of those names meets the stored one.
- **Neutral / follow-ups:** a change to the m4i types is a new type version or a model patch in the server. `m4i_atlas_core` is then no longer where they are defined.

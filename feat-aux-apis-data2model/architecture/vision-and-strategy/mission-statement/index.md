# Mission Statement

Aurelius Atlas exists to make data governance of the data lake work the way its users already know — so people can find and trust their data without waiting on IT — on a stack one small team can operate and extend.

The business promise is agility: faster access to information, less dependency on IT, and data assets organisations can act on. The catalogue delivers that as a single source of truth on data assets: where data lives, who is accountable for it, how it moved and changed, and how sensitive it is.

The interface stays business-user-friendly and familiar, so nobody has to relearn it; existing clients, integrations, and muscle memory keep working while the implementation underneath is replaced ([ADR 046](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Every visible difference is a recorded [deviation](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/conversion/deviations/index.md>), never a silent one.

> [!NOTE]
>
> **What the fidelity promise does not cover**
>
> Fidelity is the REST wire format and the dashboard — the paths a client and a user touch. The Kafka notification stream and hook messages that surrounded Atlas are out of scope ([DV-01](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/conversion/deviations/index.md>), [ADR 050](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)); integrations that watched the feed poll the API instead.

Keeping that promise affordable is the engineering mission. The system of record is one search store — Elasticsearch 9 — replacing the JanusGraph, HBase and Solr assembly that made self-hosted Atlas hard to run ([ADR 047](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)). The system carries only what the catalogue needs: one HTTP service, one dashboard, one store, shared identity, and self-observation ([ADR 050](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)).

> [!NOTE]
>
> **Why replace the store assembly at all?**
>
> Because operating it is the job Atlas made the user take on: a graph database, a column store, and a search index must each be deployed, versioned, tuned, backed up, and kept consistent with the others. Catalogue data answers five verbs — write, read, search, traverse, classify — and ADR 047's argument is that one search store serves all five, so self-hosting becomes running one service and one store.

The standing promise to its users is fidelity: a ported behaviour is accepted only when parity scenarios — expected responses read from the Atlas 2.4.0 source code and its tests ([ADR 052](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)) — prove the new system behaves like the old one, and the conversion proceeds in specified, reviewed increments ([ADR 051](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)).

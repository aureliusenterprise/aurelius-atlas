# 068. A catalogue bootstraps only the metamodel it serves

- **Status:** Proposed
- **Date:** 2026-11-19
- **Deciders:** Aurelius Enterprise

## Decision

A new Aurelius Atlas catalogue starts with exactly the types its own products serve: the Apache Atlas base
model, the glossary model, and the m4i data dictionary. The vendored copies of the other Apache Atlas domain
models (Hadoop, Hive, Kafka, Spark, RDBMS, cloud, machine-learning, and Couchbase types) leave the shipped
bootstrap, and the Aurelius connector and kubernetes type names (the `m4i_kafka_*`, `m4i_elastic_*`,
`m4i_confluent_*` and `m4i_kubernetes_*` family) leave every part of the system that still assumes them: the
webapp's icon map and the lineage model's process family.

Sharp edges, named here on purpose:

- Types already stored in an existing catalogue are not deleted. A catalogue created before this change keeps
  its domain types until its owner clears the store.
- The legacy Hive special case of the replication audit key goes with the Hive types (DV-179). Replication
  audits key on the entity's own GUID for every type.
- A connector that still writes connector-typed entities lands those types as new ones, the way any unknown
  type does. The legacy products deprecated those types, so no Aurelius product sends them.
- An operator can restore any Apache Atlas model set by pointing the server's models directory at a copy of
  `addons/models`. The loader still reads whatever directory it names.

## Context

The server loads its bootstrap types from two directories that ship with it: Apache Atlas 2.4.0's
`addons/models` and the Aurelius m4i data dictionary. The Atlas copy carries 207 definitions, and 170 of them
describe systems no Aurelius product reads or writes: Hive tables, Spark jobs, S3 buckets, Couchbase
buckets. The sample data, the three scanners, the dashboards and the webapp use only the base model, the
glossary model and the m4i types. The connector and kubernetes types went further: the legacy Aurelius
dashboard deprecated them, and ADR
[058](./058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md) left them behind with the legacy
`m4i_atlas_core` products. Only two loose ends still name them: the webapp's icon map (ported verbatim) and
the lineage model's process family (ported verbatim, LM-03).

Every catalogue and every tenant store pays to load, store and list the 170 dead types. They clutter the type
listings, the search facets, and the metrics that a governance user reads. The template's rule that modules
be removable ([ADR 002](./002-modules-are-removable-slices.md)) applies to whole model sets too.

## Requirements

- R1: A new catalogue can take the existing Aurelius data (the sample corpus, every scanner's output) with no
  manual step.
- R2: Every ported Apache Atlas REST behaviour over the surviving types stays unchanged (ADR
  [046](./046-the-catalogue-keeps-its-public-contract.md)).
- R3: An existing catalogue keeps its types and its data. Nothing in this decision deletes stored data.
- R4: An operator who wants the full Apache Atlas model set can have it without a code change.
- R5: No Aurelius screen or service breaks when it meets a type name it never heard of.

## Alternatives

- **Keep everything as it is.** It meets R1 to R5, but every catalogue keeps 170 types nothing serves, which
  is the cost this decision exists to remove. It fails no requirement, so the requirement list alone does not
  settle it: the governance user's listings and the per-tenant load time settle it.
- **Ship the domain models as an opt-in package the operator installs.** It meets R4 through an install step
  instead of a directory setting, but it adds a packaging axis (a second artifact per release) that the models
  directory already covers, and R4 is met today by the setting alone.
- **Delete the stored domain types from existing catalogues at upgrade.** It fails R3 outright: it destroys
  data an owner may hold.
- **Keep the connector names in the icon map and the lineage family.** It fails R5's intent: the code keeps
  dead names that say the deprecated types are first-class, and reviewers keep re-checking whether a
  connector product needs them.

## Tradeoffs

- **Positive:** a new catalogue lists only types someone uses. Bootstrap gets smaller (about 196 JSON files
  and their patches leave the image), and per-tenant store provisioning loads a fraction of the definitions.
  The webapp and lineage code stop carrying verbatim legacy names.
- **Negative:** a customer who restores a domain model through the models directory also opts back into the
  legacy replication audit keying that DV-179 drops for the shipped set (they key on GUID either way; the
  Hive grouping simply does not come back). Parity work on a domain model would need its models restored and
  its own increment.
- **Neutral / follow-ups:** ADR 058's sentence that the connector types "stay with the products that describe
  those systems" is superseded by this record once a person accepts it. If a future connector needs the
  deprecated types, it ships them in its own models directory as an increment of its own.

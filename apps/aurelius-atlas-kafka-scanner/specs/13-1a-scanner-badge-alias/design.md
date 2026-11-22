# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-826. The scanner writes the badge alias on the two browsed entities

- **Status:** Proposed
- **Increment:** 13.1a
- **Date:** 2026-11-22

**Decision.** The graph builder writes `typeAlias` on two entity kinds and nowhere else: the
Collection carries `Kafka Cluster` and each Dataset carries `Kafka Topic` (KSA-01). The System and
the fields carry no alias, so their badges keep showing the type names `System` and `Data Field`.
The values are constants in `graph.py`, not settings.

**Reason.** `typeAlias` is the attribute 18.1 made every badge read (MMS-09, DD-721), and the
Collection and the Dataset are the two levels a person browses: the qualified name says
`kafka-broker--abc123--orders`, and the badge should read _Kafka Cluster_ and _Kafka Topic_ rather
than _Collection_ and _Dataset_ — the metamodel nouns say nothing about Kafka. The System stays
unaliased because its name is the operator's `SYSTEM_NAME`, which can legitimately read
`Data Platform Prod`; a `Kafka System` alias would fight that label and the Collection's badge for
the same word, because the cluster id names the Collection, not the System (KSC-03). A field
stays unaliased because field cards open inside a topic, where the Kafka context is already on
screen. Constant values, not settings: an alias is what the entity _is_, and a per-deployment knob
would fork the badges of one catalogue for no asked-for benefit.

**Alternatives.** `Topic` and `Cluster` alone: shorter, but a results list mixes connectors, and
the alias exists to say which system a Dataset belongs to. `Kafka Broker` on the System: the
default `SYSTEM_NAME` says broker, and the Collection's name does not, so the two levels would
read one cluster with two different vocabularies. A display-side map from type name to alias in
the webapp: refused — it would rename every `m4i_dataset`, including the tables the db-scanner
registers, and MMS-09's whole point is that the entity owns its badge text. A Helm value per
alias: nothing asked for it (spec's not-delivered table).

**Consequences.** The aliases ride the same bulk request as the tree, so a catalogue registered
before this change gains them on its next scan — the re-scan resolves the entity by its unique
qualified name and updates the attributes (KSA-02, KSC-07). The attribute changes no qualified
name, no end, and no type, so the KSC-07 scenarios and the store's unchanged-skip are untouched.
An alias never reaches a facet, filter, or query: those group by type name, so the type facet
still reads `Dataset` (MMS-09's scope). The db-scanner is free to adopt the same shape —
`Database Schema`, `Database Table` — as its own increment; nothing here makes it do so.

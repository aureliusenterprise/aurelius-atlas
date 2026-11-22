# 13.1a The scanner's tree carries its badge alias

- **Status:** in review
- **Pull request:** [#450](https://github.com/aureliusenterprise/aurelius-atlas/pull/450)
- **Records:** adds KSA-01..03 and DD-826 (here); relies on 13.1 (KSC-03, KSC-07, DD-466),
  18.1 (MMS-09, DD-721, the card's `typeAlias`), and DV-192 (this ledger row).

## Scope

13.1 hangs the scan's tree — System, Collection, Dataset, Field — and every badge then shows the
metamodel type: a Kafka topic's card reads _Dataset_ and the cluster's reads _Collection_. 18.1
(MMS-09) made the badges read the entity's own `typeAlias` attribute in place of the type name.
This increment writes that attribute on the two entities a reader browses, so the same badges read
_Kafka Topic_ and _Kafka Cluster_ (DV-192).

It delivers:

- The Collection's alias `Kafka Cluster` and each Dataset's alias `Kafka Topic`, written in the
  same bulk request as the tree (KSA-01).
- The qualified names untouched, so a re-scan still updates in place and an unchanged tree still
  skips whole (KSA-02, KSC-07).
- The e2e proof that the stored entities carry the aliases (KSA-03).

It does not deliver:

| Not delivered                                       | Lands with                         |
| --------------------------------------------------- | ---------------------------------- |
| An alias on the System or on a Field                | not planned (KSA-01, DD-826)       |
| The db-scanner's aliases (`Database Table`, …)      | its own increment                  |
| Aliases a deployment chooses                        | only if a deployment asks (DD-826) |
| An alias chosen by type in the webapp's display map | refused (DD-826)                   |

## Semantics

`typeAlias` is the optional string attribute of `m4i_referenceable` that the badges read (MMS-09).
The metamodel is unchanged, and every entity of the tree already inherits the attribute.

| Id     | Rule                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| KSA-01 | The Collection's attributes carry `typeAlias` with the value `Kafka Cluster`, and each Dataset's attributes carry it with the value `Kafka Topic`. The System and the fields carry no `typeAlias`, so their badges show the type name alone. |
| KSA-02 | The aliases change no qualified name and no end, so the scan's identity rules are unchanged: a re-scan updates the same entities in place and an unchanged tree is still skipped whole (KSC-07).                                             |
| KSA-03 | A stored Collection and Dataset answer their alias through the read door, so every badge — the card, the editor's static type, the details header — shows it, and the badge's icon stays resolved from the raw type name (MMS-09).           |

## Java origin

This ports nothing. Apache Atlas 2.4.0 has no Kafka scanner, and the Aurelius legacy scanner's
`sources/kafka/` wrote no `typeAlias` (13.1's "Ported from" names the source). The display idea is
the legacy dashboard's own: a badge shows an entity's alias when it carries one (DV-167).

## Deviations

DV-192: the scanner writes the two aliases on the entities it registers. Apache Atlas has no Kafka
scanner, and the Aurelius legacy scanner registered its tree without aliases.

## Acceptance

| Ids    | Proven by                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| KSA-01 | `tests/test__graph.py` (the two aliases, and no alias on the System or a field), `tests/test__scan.py` (the scan door receives them)             |
| KSA-02 | `tests/test__graph.py` (the unchanged qualified names), `e2e/` (a re-scan still updates in place — 13.1's KSC-07 scenario is the standing proof) |
| KSA-03 | `e2e/test__kafka_scanner_e2e.py` (the stored Collection and Dataset answer their alias)                                                          |
